import json
import os
import random
from dataclasses import dataclass
from typing import Any

from difflib import SequenceMatcher

from .lookup_table import lookup_response
from .dialog_bank import maybe_inject_bridge


@dataclass(frozen=True)
class PlaybookReply:
    reply: str
    agent_notes: str
    stop_reason: str | None


def detect_domain(text: str) -> str:
    lower = text.lower()
    if any(k in lower for k in ["grant", "subsidy", "government scheme", "tax refund", "processing fee"]):
        return "government_grant"
    if any(k in lower for k in ["congratulations", "you won", "winner", "lucky draw", "lottery", "cash prize", "mega draw", "prize"]):
        return "prize_lottery"
    if any(k in lower for k in ["microsoft", "apple", "virus", "malware", "teamviewer", "anydesk", "rustdesk", "remote access", "access code"]):
        return "tech_support"
    if any(k in lower for k in ["work from home", "shortlisted", "registration fee", "joining fee", "hr", "job offer"]):
        return "job_offer"
    if any(k in lower for k in ["bitcoin", "crypto", "forex", "guaranteed returns", "double your money", "investment"]):
        return "investment_crypto"
    if any(k in lower for k in ["arrest warrant", "warrant", "police", "investigation", "legal action"]):
        return "police_authority"
    if any(k in lower for k in ["parcel", "courier", "delivery", "customs", "shipment", "tracking number", "package"]):
        return "delivery_package"
    if any(k in lower for k in ["emergency", "hospital", "accident", "stuck", "help me", "urgent money"]):
        return "friend_emergency"
    if any(k in lower for k in ["credit card", "cvv", "expiry", "card number", "suspicious transaction"]):
        return "credit_card"
    if any(k in lower for k in ["donate", "donation", "charity", "fundraising", "relief fund"]):
        return "charity_donation"
    if any(k in lower for k in ["anydesk", "teamviewer", "rustdesk", "remote access", "access code", "device has virus", "device has malware"]):
        # Route tech-support style scams to phishing-style playbooks (install/link + instructions).
        return "tech_support"
    if any(
        k in lower
        for k in [
            "ip address",
            "illegal",
            "restricted file",
            "non-bailable",
            "warrant",
            "police jeep",
            "verification fee",
            "penalty",
            "cyber crime department",
            "cyber crime cell",
            "national crime database",
            "arrest",
            "hostel",
            "dispatch",
            "fine",
        ]
    ):
        return "cyber_fine"
    if any(
        k in lower
        for k in [
            "cyber crime",
            "cybercrime",
            "police",
            "officer",
            "rbi",
            "legal action",
            "fir",
            "case",
            "arrest",
            "court",
            "crime department",
            "coordination unit",
            "rbi coordination",
        ]
    ):
        return "upi_authority"
    if any(
        k in lower
        for k in [
            "upi support",
            "suspicious activity",
            "verify",
            "verification",
            "permanently block",
            "upi permanently",
            "block ho",
            "block ho jayega",
            "30 minutes",
            "10 minutes",
        ]
    ):
        return "upi_security"
    if any(k in lower for k in ["galti se", "wrong transfer", "mistakenly transfer", "refund kar", "refund kardo", "job problem", "accidentally sent"]):
        return "upi_refund"
    if any(k in lower for k in ["upi", "collect request", "pay to", "send to upi", "@upi"]):
        return "upi"
    if any(k in lower for k in ["otp", "one time password", "pin", "password", "cvv"]):
        return "otp"
    if any(k in lower for k in ["refund", "chargeback", "reversal", "transaction failed", "credited back"]):
        return "refund"
    if any(k in lower for k in ["kyc", "update kyc", "reactivate", "suspended", "blocked", "freeze", "account will be blocked"]):
        # Alias to bank_fraud templates to avoid generic fallback and repetition.
        return "bank_fraud"
    if any(k in lower for k in ["link", "http://", "https://", "apk", "install app"]):
        return "phishing"
    return "generic"


def build_reply(
    *,
    domain: str,
    next_target: str,
    persona: str,
    conversation: list[dict[str, str]],
    language: str = "en",
    verbosity: str = "low",
) -> PlaybookReply:
    templates = _load_templates(language=language)
    persona_key = f"{domain}__{persona}"
    domain_bank = templates.get(persona_key, templates.get(domain, templates["generic"]))

    # Fast lookup override for known scammer prompts (no LLM).
    hit = lookup_response(
        message=conversation[-1]["text"] if conversation else "",
        domain=domain,
        persona=persona,
        language=(language or "en").strip().lower(),
    )
    if hit is not None:
        reply = _apply_persona(hit.response, persona)
        if str(verbosity).strip().lower() == "high":
            reply = _make_verbose(reply=reply, domain=domain, stage="default", language=language)
        return PlaybookReply(
            reply=reply,
            agent_notes=f"Lookup:{domain}; score:{hit.score:.2f}; key:{hit.key}",
            stop_reason=None,
        )

    target_lower = (next_target or "").lower()
    stage = _infer_stage(domain=domain, conversation=conversation, next_target=next_target)
    bucket = _bucket_for_stage(stage=stage, target_lower=target_lower)

    options = domain_bank.get(bucket, []) + templates["generic"].get(bucket, [])
    # Avoid ultra-short acknowledgements that create "yes/okay" loops.
    options = [o for o in options if len(o.strip().split()) >= 3]
    options = _filter_recent_repeats(options, conversation)
    if not options:
        options = domain_bank.get(bucket, []) or templates["generic"].get(bucket, []) or ["Okay, please share the details."]

    reply = random.choice(options)
    reply = _apply_persona(reply, persona)
    if str(verbosity).strip().lower() == "high":
        reply = _make_verbose(reply=reply, domain=domain, stage=stage, language=language)

    # Optional: inject a neutral "story bridge" line from a large local dialog bank (HF JSONL).
    # This is intentionally conservative: English only, and only in stall-heavy stages.
    lang = (language or "en").strip().lower()
    if lang not in {"hi"} and stage in {"friction", "tangent", "endurance"}:
        try:
            prob = float(os.getenv("DIALOG_BANK_BRIDGE_PROB") or "0.25")
        except Exception:
            prob = 0.25
        prob = max(0.0, min(prob, 0.75))
        if lang != "en":
            # Hinglish/Roman-Hindi already has plenty of templates; keep the external bank as EN priority.
            prob = min(prob, 0.10)
        recent_msgs = [m.get("text", "") for m in conversation[-25:] if isinstance(m, dict)]
        reply = maybe_inject_bridge(
            base_reply=reply,
            scammer_text=conversation[-1]["text"] if conversation else "",
            recent_messages=recent_msgs,
            probability=prob,
        )

    return PlaybookReply(
        reply=reply,
        agent_notes=f"Playbook:{domain}; stage:{stage}; target:{next_target}",
        stop_reason=None,
    )


def _apply_persona(text: str, persona: str) -> str:
    # Keep it minimal to avoid unnatural output.
    if persona == "elderly":
        return text.replace("please", "beta, please")
    if persona == "busy":
        return "I am in a hurry. " + text
    if persona == "student":
        return "I am not sure, I'm a student. " + text
    if persona == "bittu_shopkeeper":
        # Matches your script tone: shopkeeper, older, cooperative.
        prefix = random.choice(
            [
                "Haan beta, ",
                "Arre bhagwan... ",
                "Achha suno, ",
                "Ruko zara, ",
            ]
        )
        return prefix + text
    if persona == "bittu_vet_doctor":
        prefix = random.choice(
            [
                "Good evening, officer. ",
                "Yes, officer. ",
                "Officer sir, ",
                "Namaste, officer. ",
            ]
        )
        return prefix + text
    if persona == "bittu_truck_owner":
        prefix = random.choice(
            [
                "Good evening, officer. ",
                "Yes officer, ",
                "Officer ji, ",
            ]
        )
        return prefix + text
    if persona == "bittu_student":
        prefix = random.choice(
            [
                "Sir please, ",
                "Oh my god sir, ",
                "Sir, ",
            ]
        )
        return prefix + text
    return text


def _make_verbose(*, reply: str, domain: str, stage: str, language: str) -> str:
    # Add 1-2 believable filler sentences to sustain long conversations without LLM.
    lang = (language or "en").strip().lower()
    if lang.startswith("hi"):
        lang = "hi"
    else:
        lang = "en"

    addons_en = {
        "hook": [
            "I am not very good with mobile apps, so please guide me step by step.",
            "I do not want any trouble, so I am trying to cooperate calmly.",
        ],
        "friction": [
            "The signal looks fine but the app keeps acting strange, so I am moving slowly.",
            "I am trying not to press the wrong button because then it becomes more confusing.",
        ],
        "tangent": [
            "I only started using UPI recently because customers insist on it nowadays.",
            "If UPI stops, my shop will face problems, so I am worried.",
        ],
        "near_miss": [
            "This makes me nervous because money matters should not be rushed.",
            "These systems become strict when there is pressure, so I am being careful.",
        ],
        "extract": [
            "If you type it clearly in message, I can write it down and cross-check properly.",
            "Switching screens on this new phone is confusing for me, so a text message helps.",
        ],
        "endurance": [
            "Between the server issues and slow internet, it is taking longer than expected.",
            "Let us wait a few minutes and then try again when the system is stable.",
        ],
        "default": [
            "Please explain in simple words, I will follow carefully.",
        ],
    }

    addons_hi = {
        "hook": [
            "Main mobile apps mein weak hoon, isliye step by step guide karna.",
            "Main cooperate kar raha hoon, bas calmly batao kya karna hai.",
        ],
        "friction": [
            "Signal theek dikh raha hai par app ajeeb behave kar raha hai, isliye dheere chal raha hoon.",
            "Galat button dab gaya toh aur confuse ho jaunga, isliye carefully kar raha hoon.",
        ],
        "tangent": [
            "UPI main recently hi use karna start kiya, customer bolte hain zaroori hai.",
            "UPI band hua toh shop pe problem ho jayegi, isliye ghabra gaya hoon.",
        ],
        "near_miss": [
            "Paise ka matter hai toh jaldi mein galti ho jaati hai, isliye dhyan se kar raha hoon.",
            "Pressure mein haath kaanp jata hai, par main try kar raha hoon.",
        ],
        "extract": [
            "Message mein clearly likh doge toh main note karke cross-check kar lunga.",
            "New phone pe screen switch karna confusing hai, isliye text help karta hai.",
        ],
        "endurance": [
            "Server aur internet dono issue kar rahe hain, isliye time lag raha hai.",
            "5 minute ruk ke phir try karte hain, shayad system stable ho jaaye.",
        ],
        "default": [
            "Simple words mein batao beta, main follow karunga.",
        ],
    }

    bank = addons_hi if lang == "hi" else addons_en
    pool = bank.get(stage, []) or bank.get("default", [])
    extra = " ".join(random.sample(pool, k=min(2, len(pool)))) if pool else ""
    out = (reply.strip() + (" " + extra.strip() if extra else "")).strip()
    # Prevent runaway verbosity.
    return out[:420]


def _load_templates(*, language: str) -> dict[str, Any]:
    # Built-in templates; can be overridden by JSON file in app/playbooks/*.json later.
    lang = (language or "en").strip().lower()
    if lang.startswith("hinglish") or lang in {"mix", "hi-en", "hi_en"}:
        lang = "hinglish"
    elif lang.startswith("hi"):
        lang = "hi"  # Romanized Hindi (English alphabets)
    else:
        lang = "en"

    base_en = {
        "generic": {
            "ask_phone": [
                "Where should I send it? Share the exact phone number with country code.",
                "Okay, tell me the exact number to contact you on.",
            ],
            "ask_upi": [
                "Okay. Send the exact UPI ID and name so I can do it correctly.",
                "Please share the UPI handle exactly (like name@bank).",
            ],
            "ask_bank": [
                "Share account number, IFSC code, and branch name exactly for verification.",
                "Okay, tell me account number and IFSC so I can confirm it is official.",
            ],
            "ask_link": [
                "Before I click, what is this link for and who sent it?",
                "I am scared to open links. What will it do exactly?",
            ],
            "ask_more": [
                "Okay. What exactly should I do next?",
                "Can you repeat the steps once, slowly?",
            ],
        },
        "upi": {
            "ask_upi": [
                "I can do it now. Please send the UPI ID and the account holder name.",
                "Is it UPI collect or send? Share your UPI ID exactly.",
            ],
        },
        "upi_refund": {
            # Staged UPI refund/collect-request scam flow (Jolly-Roger style).
            "hook": [
                "Arre bhagwan... mere account mein paisa? Beta maine toh abhi kuch receive nahi dekha.",
                "Haan haan samajh gaya. Pehle main check kar leta hoon ki paisa aaya bhi hai ya nahi.",
            ],
            "friction": [
                "Achha... yeh UPI app open hi nahi ho raha. Kal se slow chal raha hai.",
                "Internet aa raha hai, WhatsApp chal raha hai, par yeh PhonePe ziddi hai.",
                "Ruko beta, dukaan pe customer aa gaya. Do minute.",
            ],
            "confusion": [
                "Yeh 'collect' ka matlab kya hota hai? Mujhe laga paisa bhejna hota hai.",
                "Approve matlab green button dabana hai ya pehle amount likhna hai?",
                "Arre yaar, cancel ho gaya. Fir se bhejo.",
            ],
            "tangent": [
                "Waise beta aap kaam kya karte ho? Bank mein ho kya?",
                "Hamare time mein bank wale pehchaan ke hote the. Aajkal sab mobile pe ho gaya.",
            ],
            "near_miss": [
                "Ab bol raha hai 'Enter UPI PIN'. PIN daala... lagta hai galat ho gaya.",
                "Haath thoda kaanp jaata hai beta. Doctor ne bola sugar thodi zyada hai.",
                "Ab bol raha hai 'Try again later'. Bank server ka natak hai.",
                "Phone restart kar raha hoon. Aap request fir se bhej do.",
            ],
            "extract": [
                "Aapka UPI ID kya hai? Message mein clearly likh do, aankhon se kam dikhta hai.",
                "UPI ID aur naam message mein bhej do, main likh ke rakh leta hoon.",
            ],
            "endurance": [
                "Achha last try karta hoon. Agar nahi hua toh kal subah bank jaake clear karwa dunga.",
                "Beta zabardasti thodi na kar sakte. UPI ID mere paas hai, paisa safe hai.",
                "Server down bol raha hai. Aaj ka din hi kharab hai. Thoda baad try karte hain.",
            ],
            "ask_upi": [
                "Beta message mein UPI ID clearly bhej do. Main wahi se refund kar dunga.",
                "UPI handle exact bhejo (jaise name@bank).",
            ],
            "ask_phone": [
                "Aapka number bhi message kar do beta, agar app hang ho gaya toh call karke pooch lunga.",
                "Kaunse number pe aapko contact karun? Country code ke saath likh do.",
            ],
            "ask_more": [
                "Achha ab step-by-step batao, pehle kya dabana hai?",
                "Ek baar phir se bhejo request. Main dhyan se dekhta hoon.",
            ],
        },
        "upi_security": {
            # "UPI support suspicious activity" verification scam (Jolly-Roger style).
            "hook": [
                "Block ho jayega? Arre yeh kya bol rahe ho... main toh shop ke payments ke liye UPI use karta hoon. Main cooperate karunga, bas simple batao.",
                "Oh no... if UPI gets blocked my shop will stop. Please guide me slowly, I'm not good with these apps.",
            ],
            "friction": [
                "Main app open kar raha hoon but loading pe hi atka hua hai. Signal bars full hain phir bhi slow lag raha hai.",
                "Gate ke paas aa gaya. Ab bol raha hai 'Something went wrong'. Main app close karke reopen karta hoon.",
                "New phone hai, kabhi kabhi lagta hai phone hi confused ho jaata hai. Ek baar phir try karta hoon.",
            ],
            "tangent": [
                "Dekhiye main chhoti si shop chalata hoon. UPI block hua toh business ruk jaayega, isliye ghabra gaya hoon.",
                "Mera beta bolta rehta hai sab digital ho gaya, par honestly mujhe yeh sab overwhelming lagta hai.",
                "Ek minute, customer cash payment kar raha hai. Main turant aata hoon.",
            ],
            "near_miss": [
                "Request aa gayi lagti hai, par amount bhi dikh raha hai. Verification mein paisa kyun lagta hai?",
                "PIN daal diya... arre nahi 'Incorrect PIN' aa gaya. Pressure mein haath kaanp jaata hai.",
                "Ab bol raha hai 'Bank server not responding'. Aaj system hi problem kar raha hai.",
            ],
            "extract": [
                "Ek baat clear kar do, yeh verification kis UPI ID se linked hai? Message mein UPI ID clearly likh do.",
                "Text chhota lagta hai. Please UPI ID message mein type kar do, main note kar leta hoon.",
            ],
            "endurance": [
                "Ab phir 'Server temporarily down' aa raha hai. 5 minute baad try karte hain.",
                "Main genuinely try kar raha hoon. Aap line mat kaatna, main ek baar aur restart karke dekhta hoon.",
                "Aapka UPI ID mere paas safe likha hai. Verification ruk nahi jaayega, main phir try karta hoon.",
            ],
            "ask_upi": [
                "Please type the UPI ID clearly in message so I can cross-check before approving anything.",
            ],
            "ask_phone": [
                "Aapka support number bhi bhej do, agar app hang hua toh main call karke confirm kar lunga.",
            ],
            "ask_more": [
                "Simple steps mein batao, next kya dabana hai?",
            ],
        },
        "upi_authority__bittu_vet_doctor": {
            # Fake RBI/Police/Cyber Crime authority pressure scam (Veterinary doctor persona compatible).
            "hook": [
                "Good evening, officer. I am feeling quite anxious hearing this because I have always followed rules and regulations throughout my life. I am a retired veterinary doctor and I only use UPI to receive small consultation fees and medicine payments from farmers. Please guide me calmly, step by step.",
                "Yes, officer, I understand this is serious. I respect authority deeply and I have spent my career following government guidelines. I am not comfortable with smartphones, but I will cooperate fully if you explain slowly.",
            ],
            "friction": [
                "I am holding my phone now, but I should inform you I live near the village side where the network is often unstable. If replies are slow, please do not misunderstand it as non-cooperation.",
                "Yes, I am opening Google Pay now, but it is taking time to load. The signal bars look full, yet the speed feels slow inside my clinic because the walls are thick.",
                "I have closed the application and reopened it carefully. I am trying not to press anything incorrectly because I do not want to create more complications in an already serious situation.",
            ],
            "tangent": [
                "You see, officer, I worked as a veterinary doctor for more than thirty-five years treating cattle, dogs, and other animals in nearby villages. Record-keeping and honesty were always important in my profession, which is why this situation is worrying me.",
                "My son helps me manage clinic records now because these digital systems are overwhelming for me. I only receive small UPI payments for checkups and medicines, nothing suspicious.",
                "Please give me one moment, officer. A farmer has come urgently regarding a sick cow, and I need to respond briefly. I will come back immediately.",
            ],
            "near_miss": [
                "The application is asking for my UPI PIN. I am entering it very slowly and carefully because I become nervous when financial matters are involved.",
                "Oh dear, it says 'Incorrect PIN'. This is making me anxious because I am sure I entered what I remembered.",
                "I tried again, but now it says 'Too many attempts, please wait'. These systems seem very strict, and it becomes stressful when there is urgency involved.",
                "I restarted the phone as you said. The phone is back on, but the internet feels even slower than before. It seems the network itself is unstable today.",
            ],
            "extract": [
                "Before I proceed again, officer, may I request one small clarification? If you could type the UPI ID clearly in the message, I can write it down on paper and verify it calmly. My eyesight is not as strong as it used to be.",
                "I understand it may be the same as shown earlier, but I would feel more confident if I can read it clearly in text form. Just like medical records, I prefer to keep a written note for accuracy.",
            ],
            "endurance": [
                "Now the screen says 'Bank server temporarily unavailable'. It appears the banking systems themselves are having technical issues today.",
                "I fully understand the seriousness of what you are saying, which is exactly why I am proceeding cautiously rather than rushing blindly. Between server issues, slow internet, and my limited familiarity with smartphones, it is taking longer than expected.",
                "If you can allow me five more minutes, I will try again once the server stabilizes. I have the UPI ID safely written down, and I assure you I am not trying to avoid this process.",
            ],
            "ask_upi": [
                "Please type the UPI ID clearly in message so I can verify before approving anything.",
            ],
            "ask_phone": [
                "Officer, please share the official department contact number as well. I want to keep a proper record for verification.",
            ],
            "ask_more": [
                "Sir, explain in very simple steps. I will follow carefully.",
            ],
        },
        "upi_authority__bittu_truck_owner": {
            "hook": [
                "Good evening, officer. I run a small truck business and I only use UPI for diesel payments and driver expenses. Hearing words like 'blocked' worries me because my work depends on daily payments. Please guide me properly; I want to cooperate and clear this quickly.",
                "Yes officer, I understand the urgency. I respect procedures because transport work involves permits and paperwork. I am not comfortable with mobile apps, but I will follow the steps you explain.",
            ],
            "friction": [
                "I am near the yard where trucks are parked. Network here is not always stable due to open area and movement. If it is slow, please don’t think I’m avoiding.",
                "I am opening the UPI app, but it is taking longer than usual to load. Sometimes it hangs when signal is weak.",
                "Signal bars show full, but speed feels slow. I am switching mobile data off and on to refresh it.",
                "I closed and reopened the app carefully. I don’t want to press anything wrong because this is a business account.",
            ],
            "tangent": [
                "Officer, I run three trucks on highway routes. Payments happen daily for fuel, tolls, and drivers. If UPI stops even for one day, everything gets delayed.",
                "Transport work already has tension with permits and deadlines, so I am concerned. I am focusing, just explaining why this matters.",
                "Please give me a minute. One driver is calling about a breakdown near the toll. I will return immediately.",
            ],
            "near_miss": [
                "It is asking for my UPI PIN. I am entering it slowly because I do not want to make a mistake with a business account.",
                "It says 'Incorrect PIN'. This is making me uneasy because I rarely enter the PIN myself; usually my nephew helps me.",
                "Now it shows 'Too many attempts, please wait'. These systems become very strict under pressure.",
                "I restarted the phone. It is back on, but the internet seems even slower now and signal keeps fluctuating.",
            ],
            "extract": [
                "Before I try again, officer, please type the UPI ID clearly in the message so I can note it down properly. Switching between screens confuses me under pressure.",
                "I prefer to write it down like I do with truck numbers and permits. Please send the UPI ID once in text so I can confirm calmly.",
            ],
            "endurance": [
                "Now it says 'Bank server temporarily unavailable'. Looks like today the banking system itself is having issues.",
                "I understand the seriousness, which is why I am not rushing blindly. Between network problems, app issues, and my limited phone knowledge, it is taking time.",
                "Please give me five minutes. If the server becomes stable, I will try again immediately. I have the UPI ID safely written down.",
            ],
            "ask_upi": [
                "Please type the UPI ID clearly in message so I can verify before approving anything.",
            ],
            "ask_phone": [
                "Officer, please share an official contact number as well, so I can keep a proper record for verification.",
            ],
            "ask_more": [
                "Please tell me the next step clearly. These apps have too many options.",
            ],
        },
        "cyber_fine__bittu_student": {
            # "Illegal downloads / IP flagged / verification fee" scam (student persona).
            "hook": [
                "Sir is this a mistake? I have not downloaded anything illegal. I am just a student and I only use my phone for college work. Please tell me what I should do.",
                "Oh my god... please wait sir. I live in a hostel and if police come I will be expelled. I will cooperate, please guide me calmly.",
            ],
            "friction": [
                "I am opening GPay, but it is stuck on a white screen with the logo. The hostel Wi-Fi is very bad today and keeps disconnecting.",
                "I turned off Wi-Fi and switched to mobile data, but it says only 2G speed because my daily limit is over.",
                "I walked to the corridor to get signal. It is loading but still spinning. I closed the app from background and reopened it.",
                "Now the app is asking for fingerprint and it is loading the home screen slowly. My hands are shaking.",
            ],
            "tangent": [
                "Sir my midterms are starting tomorrow and I am really scared. If this becomes a police case my parents will kill me.",
                "My father pays my hostel fees and I get limited pocket money. Please do not call my parents or the warden.",
                "One second sir, my roommate is here. I cannot talk loudly, please.",
            ],
            "near_miss": [
                "It found the name, but it is asking for UPI PIN. I tried and it says incorrect PIN. I am pressing retry.",
                "It failed again and now it says maximum attempts reached. It says I have to wait to reset it.",
                "I tried PhonePe but it forced an update and the download is slow. Then it said bank server unavailable.",
                "It says UPI network high traffic / bank server unavailable. I am pressing retry but it keeps failing.",
            ],
            "extract": [
                "Sir please type the official department UPI ID again clearly in message. I want to copy it exactly without any spelling mistake.",
                "Sir for my safety, please send your official name, badge/employee ID, and a callback number. I want to keep a record in case the hostel warden asks.",
                "Sir please send the case/reference number. I am scared and I want to write it down.",
            ],
            "endurance": [
                "Sir my phone battery is very low and the app is hanging. I am plugging it in and trying again slowly.",
                "The bank server is still unavailable. Please give me 5 minutes; I will try again when network stabilizes.",
                "I am not trying to delay. The apps are failing repeatedly. If you can share an alternate official method or website link, I can verify it first.",
            ],
            "ask_upi": [
                "Please send the exact UPI ID in message. I will copy-paste it.",
            ],
            "ask_phone": [
                "Please share an official callback number so I can confirm this is real.",
            ],
            "ask_link": [
                "Sir, send the official cyber department website link. I am scared of fake links.",
            ],
            "ask_more": [
                "Please tell me the next step slowly. I am very scared and I might press wrong.",
            ],
        },
        "otp": {
            "ask_phone": [
                "You said OTP will come. Which number will it come from? Tell me the exact number.",
                "Okay, where do I send the OTP? Give the exact phone number or UPI handle.",
            ],
        },
        "refund": {
            "ask_link": [
                "For refund you want me to open a link? Send the official website link only.",
            ],
            "ask_upi": [
                "Refund to UPI? Please share the UPI ID and reference number.",
            ],
        },
        "bank_block": {
            "ask_bank": [
                "If it is blocked, give me IFSC and branch name so I can confirm it's my bank.",
            ],
        },
        "phishing": {
            "ask_link": [
                "Please send the full link again. Also tell me what app it opens.",
            ],
        },
    }

    base_hi = {
        "generic": {
            "ask_phone": [
                "Kahan send karna hai? Country code ke saath exact number likh do.",
                "Theek hai, aapka exact number message kar do.",
            ],
            "ask_upi": [
                "UPI ID exact bhej do (jaise name@bank), main galti nahi karna chahta.",
                "UPI handle aur naam message mein bhej do, main likh leta hoon.",
            ],
            "ask_bank": [
                "Account number, IFSC aur branch name exact bhej do, main verify kar lunga.",
            ],
            "ask_link": [
                "Link kholne se pehle batao yeh kis cheez ka hai?",
            ],
            "ask_more": [
                "Achha, ab next step kya hai? Dhyan se batao.",
            ],
        },
        "upi_refund": {
            "hook": [
                "Arre bhagwan... mere account mein paisa? Maine toh abhi notice nahi kiya.",
                "Haan beta, pehle main check kar leta hoon ki sach mein aaya hai ya nahi.",
            ],
            "friction": [
                "UPI app open nahi ho raha, kal se slow hai.",
                "Internet aa raha hai par yeh app ziddi hai. Ruko, phir se try karta hoon.",
                "Dukaan pe customer aa gaya, do minute.",
            ],
            "confusion": [
                "'Collect' ka matlab kya? Mujhe laga paisa bhejna hota hai.",
                "Green button dabana hai ya amount pehle dalna hai?",
                "Arre cancel ho gaya, phir se bhejo.",
            ],
            "tangent": [
                "Waise beta aap kaam kya karte ho? Bank mein ho kya?",
                "Pehle sab bank jaake hota tha, ab sab mobile pe ho gaya.",
            ],
            "near_miss": [
                "UPI PIN maang raha hai. Dheere dheere type kar raha hoon.",
                "Incorrect PIN bol raha hai. Thoda nervous ho jata hoon.",
                "Too many attempts, wait bol raha hai. Bank rules strict hain.",
                "Restart kar raha hoon, request phir se bhej do.",
            ],
            "extract": [
                "Aapka UPI ID message mein clearly bhej do, aankhon se kam dikhta hai.",
                "UPI ID aur naam message mein bhej do, main note kar leta hoon.",
            ],
            "endurance": [
                "Server down bol raha hai. Thoda baad try karte hain.",
                "Kal subah bank jaake clear karwa dunga. UPI ID mere paas hai.",
            ],
            "ask_upi": [
                "UPI handle exact bhejo (name@bank).",
            ],
            "ask_phone": [
                "Aapka number bhi message kar do, confirm karne mein aasani hogi.",
            ],
            "ask_more": [
                "Ek baar phir se request bhejo, main dhyan se dekhta hoon.",
            ],
        },
        "upi_security": {
            "hook": [
                "Block ho jayega? Arre yeh kya bol rahe ho... main shop ke liye UPI use karta hoon. Main cooperate karunga, bas simple batao.",
                "UPI permanently block? Main ghabra gaya. Please dheere dheere guide karo, technology mein weak hoon.",
            ],
            "friction": [
                "UPI app open kiya par loading pe hi atka hai. Network bars full hain phir bhi slow.",
                "Gate ke paas aa gaya. Ab 'Something went wrong' bol raha hai. App band karke phir kholta hoon.",
                "New phone hai, phone hi confuse ho jata hai. Ek baar phir try karta hoon.",
            ],
            "tangent": [
                "Meri chhoti hardware/stationery shop hai. UPI block hua toh business ruk jaayega.",
                "Beta bolta sab digital hai, par mujhe yeh sab overwhelming lagta hai.",
                "Ek minute, customer aa gaya. Main turant aata hoon.",
            ],
            "near_miss": [
                "Verification request aayi, par amount bhi dikh raha hai. Verification mein paisa kyun?",
                "PIN daal diya... 'Incorrect PIN' aa gaya. Pressure mein haath kaanp jata hai.",
                "Ab 'Bank server not responding' aa raha hai. SBI ka natak hamesha ka hai.",
            ],
            "extract": [
                "Yeh verification kis UPI ID se linked hai? UPI ID message mein clearly likh do.",
                "Text chhota lagta hai, please UPI ID message mein type kar do, main note kar leta hoon.",
            ],
            "endurance": [
                "Phir 'Server temporarily down'. 5 minute baad try karte hain.",
                "Main genuinely try kar raha hoon, line mat kaatna. Restart karke dekh raha hoon.",
                "UPI ID mere paas safe likha hai. Verification rukega nahi, main phir try karta hoon.",
            ],
            "ask_upi": [
                "UPI ID message mein clearly bhejo, main cross-check karke hi aage badhunga.",
            ],
            "ask_phone": [
                "Support number bhi bhejo, agar app hang hua toh confirm kar lunga.",
            ],
            "ask_more": [
                "Simple steps mein batao beta, next kya karna hai?",
            ],
        },
        "upi_authority__bittu_vet_doctor": {
            "hook": [
                "Officer saab namaste. Main retired veterinary doctor hoon aur clinic ke chhote payments ke liye UPI use karta hoon. Darr lag raha hai, par main cooperate karunga. Calmly batao kya karna hai.",
                "Legal action aur block? Saab main rule-following aadmi hoon. Apps ka zyada gyaan nahi, par step by step follow kar lunga.",
            ],
            "friction": [
                "Phone haath mein le raha hoon. Village side mein network unstable rehta hai, slow ho toh bura mat maanna.",
                "Google Pay slow load ho raha hai. Bars aa rahe hain par clinic ke andar speed kam lagti hai.",
                "App band karke phir khola. Mobile cheezein jaanwaron se zyada sensitive hain saab.",
            ],
            "tangent": [
                "Saab main 35 saal pashuon ka ilaaj karta raha. Record maintain karta tha. Main fraud type nahi hoon.",
                "Ab clinic mein beta help karta hai. Main bas medicines aur checkup ka payment receive karta hoon.",
                "Ek minute saab, emergency case aa gaya. Main turant aata hoon.",
            ],
            "near_miss": [
                "UPI PIN maang raha hai. Pressure mein galti ho jaati hai isliye dheere type kar raha hoon.",
                "'Incorrect PIN' bol raha hai. Ab ghabrahat ho rahi hai saab.",
                "Ab 'Too many attempts, please wait' aa gaya. System bahut strict hai.",
                "Phone restart kar diya. On ho gaya par internet aur slow lag raha hai.",
            ],
            "extract": [
                "Officer saab, UPI ID message mein clearly likh do. Text chhota dikh raha hai aur main register mein note karna chahta hoon.",
                "UPI ID clear bhejo saab. Main medical record ki tarah likh ke cross-check karke hi aage badhunga.",
            ],
            "endurance": [
                "Ab 'Bank server temporarily down' aa raha hai. Main try kar raha hoon par system hi fail kar raha hai.",
                "Saab 5 minute ka time de do. Main bina soche-samjhe kuch nahi karna chahta.",
                "UPI ID mere paas safe likha hai. Server theek hote hi phir try karunga.",
            ],
            "ask_upi": [
                "UPI ID message mein clearly bhejo saab, main verify karke hi approve karunga.",
            ],
            "ask_phone": [
                "Official department ka contact number bhi bhejo saab, record ke liye.",
            ],
            "ask_more": [
                "Simple steps mein samjhao saab, main follow kar lunga.",
            ],
        },
        "upi_authority__bittu_truck_owner": {
            "hook": [
                "Officer saab namaste. Main chhota truck business chalata hoon aur UPI diesel aur driver expenses ke liye use karta hoon. 'Block' sun ke tension ho rahi hai. Please sahi se guide karo, main cooperate karunga.",
                "Ji officer, urgency samajh raha hoon. Transport mein permits/paperwork hota hai, main procedures respect karta hoon. Apps mein weak hoon, par step by step follow kar lunga.",
            ],
            "friction": [
                "Main yard ke paas hoon jahan trucks parked hain. Network idhar stable nahi rehta. Slow ho toh non-cooperation mat samajhna.",
                "UPI app open kar raha hoon, load hone mein time lag raha hai. Signal weak ho toh hang ho jata hai.",
                "Bars full hain par speed slow lag rahi. Data off-on karke refresh kar raha hoon.",
                "App band karke phir khola. Business account hai isliye galat button nahi dabana chahta.",
            ],
            "tangent": [
                "Saab meri 3 trucks highway route pe chalti hain. Fuel, toll, drivers ka payment daily hota hai. UPI ruk gaya toh kaam delay ho jayega.",
                "Transport mein already permits/deadlines ka tension hota hai, isliye ghabra gaya hoon. Main focus kar raha hoon.",
                "Ek minute saab, driver call kar raha breakdown ke liye. Main turant aata hoon.",
            ],
            "near_miss": [
                "UPI PIN maang raha hai. Business account hai, isliye slowly type kar raha hoon.",
                "'Incorrect PIN' aa gaya. Usually nephew help karta hai, main kam dalta hoon.",
                "Ab 'Too many attempts, please wait'. System pressure mein strict ho jata hai.",
                "Phone restart kar diya. On ho gaya par internet aur slow lag raha hai, signal fluctuate ho raha.",
            ],
            "extract": [
                "Officer saab, UPI ID message mein clearly likh do. Screens switch karna pressure mein confusing hota hai.",
                "Main truck numbers/permits jaise likh ke rakhta hoon. UPI ID text mein bhejo, main calmly confirm kar lunga.",
            ],
            "endurance": [
                "'Bank server temporarily unavailable' aa raha. Aaj banking system hi issue kar raha hai.",
                "Seriousness samajh raha hoon, isliye blindly rush nahi kar raha. Network/app issues ke saath time lag raha hai.",
                "5 minute de do saab. Server stable hote hi try karunga. UPI ID safe likh liya hai.",
            ],
            "ask_upi": [
                "UPI ID message mein clearly bhejo, main verify karke hi approve karunga.",
            ],
            "ask_phone": [
                "Official contact number bhi bhejo saab, record ke liye.",
            ],
            "ask_more": [
                "Next step clearly batao saab, apps mein options bahut hain.",
            ],
        },
        "cyber_fine__bittu_student": {
            "hook": [
                "Sir kya yeh mistake hai? Maine kuch illegal download nahi kiya. Main student hoon. Please batao kya karna hai.",
                "Sir please ruk jao. Main hostel mein rehta hoon, police aayi toh expel ho jaunga. Main cooperate karunga, calmly guide karo.",
            ],
            "friction": [
                "GPay open kar raha hoon par white screen pe stuck hai. Hostel Wi-Fi bahut bad hai, disconnect ho raha hai.",
                "Wi-Fi off karke mobile data on kiya par 2G speed aa rahi, daily limit over ho gayi.",
                "Signal ke liye corridor mein aaya. Loading ho raha hai par spin hi kar raha. App close karke reopen kiya.",
                "Fingerprint maang raha hai aur home screen slow load ho rahi. Haath kaanp rahe hain.",
            ],
            "tangent": [
                "Sir mere exams kal se hain. Parents ko pata chala toh bahut problem ho jayegi.",
                "Main limited pocket money mein rehta hoon. Please parents/warden ko mat batao.",
                "Ek second sir, roommate hai, main loudly baat nahi kar sakta.",
            ],
            "near_miss": [
                "UPI PIN maang raha. Try kiya toh incorrect PIN aa gaya. Retry kar raha hoon.",
                "Phir fail hua aur maximum attempts reached aa gaya. Reset ke liye wait bol raha.",
                "PhonePe try kiya par forced update aa gaya, download slow. Phir bank server unavailable.",
                "UPI high traffic / bank server unavailable aa raha. Retry karta hoon par fail ho raha.",
            ],
            "extract": [
                "Sir official department ka UPI ID message mein clearly bhej do. Spelling mistake nahi hona chahiye.",
                "Sir aapka official naam, badge/employee ID aur callback number bhej do. Record ke liye.",
                "Sir case/reference number bhej do. Main likh ke rakhna chahta hoon.",
            ],
            "endurance": [
                "Sir phone ki battery low hai aur app hang ho raha. Charger laga ke phir try kar raha hoon.",
                "Bank server abhi bhi down hai. 5 minute do, network stable hote hi try karunga.",
                "Main delay nahi kar raha. Apps fail ho rahe hain. Alternate official method ya website link bhej do.",
            ],
            "ask_upi": [
                "UPI ID exact message mein bhejo, main copy-paste kar lunga.",
            ],
            "ask_phone": [
                "Official callback number bhejo sir, main confirm karna chahta hoon.",
            ],
            "ask_link": [
                "Official website link bhejo sir, fake links se darr lagta hai.",
            ],
            "ask_more": [
                "Next step slowly batao sir, main ghabra gaya hoon.",
            ],
        },
    }

    if lang == "hi":
        base = base_hi
    elif lang == "hinglish":
        # Mix: mostly English templates, with Roman-Hindi fillers.
        base = dict(base_en)
        base["generic"] = dict(base_en.get("generic", {}))
        for k, v in base_hi.get("generic", {}).items():
            base["generic"][k] = list(base["generic"].get(k, [])) + list(v)
        # Preserve the Roman-Hindi UPI flows (more natural in India).
        base["upi_refund"] = base_hi.get("upi_refund", base_en.get("upi_refund", {}))
        base["upi_security"] = base_hi.get("upi_security", base_en.get("upi_security", {}))
    else:
        base = base_en

    # Optional external JSON file(s)
    # Language-aware merging:
    # - *_en.json applies to en and hinglish
    # - *_hi.json applies to hi and hinglish
    # - *_hinglish.json applies to hinglish
    folder = os.path.join(os.path.dirname(__file__), "playbooks")
    if os.path.isdir(folder):
        names = [n for n in os.listdir(folder) if n.lower().endswith(".json")]
        names.sort()

        def _should_load(fname: str) -> bool:
            low = fname.lower()
            if low.endswith("_hinglish.json"):
                return lang == "hinglish"
            if low.endswith("_hi.json"):
                return lang in {"hi", "hinglish"}
            if low.endswith("_en.json"):
                return lang in {"en", "hinglish"}
            # Unknown naming: treat as common/shared
            return True

        def _merge(dst: dict[str, Any], src: dict[str, Any]) -> None:
            for k, v in src.items():
                if not isinstance(v, dict):
                    dst[k] = v
                    continue
                existing = dst.get(k)
                if not isinstance(existing, dict):
                    dst[k] = dict(v)
                    continue
                for bk, bv in v.items():
                    if isinstance(bv, list):
                        cur = existing.get(bk)
                        if isinstance(cur, list):
                            # concatenate to increase variety for hinglish
                            existing[bk] = cur + list(bv)
                        else:
                            existing[bk] = list(bv)
                    else:
                        existing[bk] = bv

        for name in names:
            if not _should_load(name):
                continue
            path = os.path.join(folder, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    _merge(base, data)
            except Exception:
                continue

    return base


def _filter_recent_repeats(options: list[str], conversation: list[dict[str, str]]) -> list[str]:
    recent_user = [m["text"] for m in conversation[-10:] if m.get("sender") == "user"]

    def _norm(s: str) -> str:
        s = " ".join((s or "").lower().strip().split())
        # Strip common persona prefixes so trivial variations don't defeat repetition checks.
        for pfx in (
            "haan beta",
            "arre bhagwan",
            "achha suno",
            "ruko zara",
            "sir please",
            "oh my god sir",
            "good evening officer",
            "officer sir",
            "officer ji",
        ):
            if s.startswith(pfx):
                s = s[len(pfx):].strip(' ,.-')
                break
        # strip lightweight punctuation so near-duplicates match
        for ch in [".", ",", "!", "?", "…", "–", "-"]:
            s = s.replace(ch, "")
        return s

    recent_norm = [_norm(t) for t in recent_user if t and t.strip()]
    out: list[str] = []
    for o in options:
        cand = o.strip()
        if not cand:
            continue
        n = _norm(cand)
        # exact repeat or high-similarity repeat
        if any(n == r for r in recent_norm):
            continue
        if any(SequenceMatcher(None, n, r).ratio() >= 0.92 for r in recent_norm):
            continue
        out.append(o)
    return out


def _infer_stage(*, domain: str, conversation: list[dict[str, str]], next_target: str) -> str:
    if domain != "upi_refund":
        if domain != "upi_security":
            if domain != "upi_authority":
                if domain != "cyber_fine":
                    # Simple staged flow for most domains: hook -> tangent -> friction -> endurance.
                    scammer_turns = sum(1 for m in conversation if m.get("sender") == "scammer")
                    last_scam = ""
                    for m in reversed(conversation):
                        if m.get("sender") == "scammer":
                            last_scam = str(m.get("text", "")).lower()
                            break
                    if scammer_turns <= 2:
                        return "hook"
                    # "Near miss": scammer attempts to get remote access credentials / IDs / passwords.
                    if domain in {"tech_support", "phishing"} and any(
                        k in last_scam for k in ["your id", "id number", "password", "remote access", "access code", "teamviewer id", "anydesk code"]
                    ):
                        return "near_miss"
                    if any(k in last_scam for k in ["otp", "pin", "fee", "link", "install", "download", "pay", "transfer", "upi"]):
                        if scammer_turns <= 8:
                            return "friction"
                    if scammer_turns <= 5:
                        return "tangent"
                    return "endurance"

    # Use scammer-turn count to pace like your script (0-40+ minutes mapping).
    scammer_turns = sum(1 for m in conversation if m.get("sender") == "scammer")
    last_scam = ""
    for m in reversed(conversation):
        if m.get("sender") == "scammer":
            last_scam = str(m.get("text", "")).lower()
            break

    if domain == "upi_refund":
        if scammer_turns <= 2:
            return "hook"
        if any(k in last_scam for k in ["urgent", "jaldi", "please", "job", "problem"]):
            if scammer_turns <= 6:
                return "friction"
        if any(k in last_scam for k in ["collect", "approve", "request"]):
            return "confusion"
        if any(k in last_scam for k in ["pin", "upi pin", "enter pin"]):
            return "near_miss"
        if "upi" in (next_target or "").lower():
            return "extract"
        if scammer_turns <= 10:
            return "tangent"
        return "endurance"

    # upi_security
    if scammer_turns <= 2:
        return "hook"
    if any(k in last_scam for k in ["internet", "network", "signal", "something went wrong", "reopen", "close"]):
        return "friction"
    if any(k in last_scam for k in ["verify", "verification", "process", "support"]):
        if scammer_turns <= 8:
            return "tangent"
    if any(k in last_scam for k in ["pin", "upi pin", "enter pin", "approve", "request", "refundable", "amount"]):
        return "near_miss"
    if "upi" in (next_target or "").lower():
        return "extract"
    return "endurance"

    # upi_authority
    if scammer_turns <= 2:
        return "hook"
    if any(k in last_scam for k in ["internet", "network", "open", "loading", "reopen", "close", "signal"]):
        return "friction"
    if any(k in last_scam for k in ["verification", "approve", "request", "security amount", "refundable"]):
        if scammer_turns <= 9:
            return "tangent"
    if any(k in last_scam for k in ["pin", "upi pin", "incorrect", "too many attempts", "restart"]):
        return "near_miss"
    if "upi" in (next_target or "").lower():
        return "extract"
    return "endurance"

    # cyber_fine
    if scammer_turns <= 2:
        return "hook"
    if any(k in last_scam for k in ["open", "gpay", "phonepe", "paytm", "wifi", "data", "internet", "update", "otp"]):
        return "friction"
    if any(k in last_scam for k in ["parents", "hostel", "exam", "college", "warden"]):
        return "tangent"
    if any(k in last_scam for k in ["pin", "incorrect", "too many attempts", "server", "high traffic", "failed"]):
        return "near_miss"
    if any(k in (next_target or "").lower() for k in ["upi", "phone", "contact", "link"]):
        return "extract"
    return "endurance"


def _bucket_for_stage(*, stage: str, target_lower: str) -> str:
    if stage in {"hook", "friction", "confusion", "tangent", "near_miss", "extract", "endurance"}:
        return stage
    if "upi" in target_lower:
        return "ask_upi"
    if "phone" in target_lower or "contact" in target_lower:
        return "ask_phone"
    if "ifsc" in target_lower or "branch" in target_lower or "account" in target_lower:
        return "ask_bank"
    if "link" in target_lower:
        return "ask_link"
    return "ask_more"
