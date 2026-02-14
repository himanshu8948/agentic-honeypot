import json
import os
import random
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PlaybookReply:
    reply: str
    agent_notes: str
    stop_reason: str | None


def detect_domain(text: str) -> str:
    lower = text.lower()
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
    if any(k in lower for k in ["kyc", "update kyc", "reactivate", "suspended", "blocked", "freeze"]):
        return "bank_block"
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
    domain_bank = templates.get(domain, templates["generic"])

    target_lower = (next_target or "").lower()
    stage = _infer_stage(domain=domain, conversation=conversation, next_target=next_target)
    bucket = _bucket_for_stage(stage=stage, target_lower=target_lower)

    options = domain_bank.get(bucket, []) + templates["generic"].get(bucket, [])
    options = _filter_recent_repeats(options, conversation)
    if not options:
        options = domain_bank.get(bucket, []) or templates["generic"].get(bucket, []) or ["Okay, please share the details."]

    reply = random.choice(options)
    reply = _apply_persona(reply, persona)
    if str(verbosity).strip().lower() == "high":
        reply = _make_verbose(reply=reply, domain=domain, stage=stage, language=language)

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
    if lang.startswith("hi"):
        lang = "hi"
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
        "upi_authority": {
            # Fake RBI/Police/Cyber Crime authority pressure scam (Veterinary doctor persona compatible).
            "hook": [
                "Officer sir, namaste. I am a retired veterinary doctor and I only use UPI for small clinic payments. I am scared, but I will cooperate. Please tell me calmly what to do.",
                "Blocked and legal action? Sir, I am a law-abiding person. I do not understand these apps much, but I will follow instructions step by step.",
            ],
            "friction": [
                "I am taking the phone now. Network is unstable on the village side, so please don’t get angry if it is slow.",
                "Google Pay is loading slowly. Signal bars are there but speed feels low inside the clinic.",
                "I closed and reopened the app. These mobile things are more sensitive than treating animals, sir.",
            ],
            "tangent": [
                "Sir, I worked 35 years treating cattle and pets. I keep proper records. I am not involved in any fraud.",
                "My son helps me at the clinic now. I only receive small payments for medicines and checkups.",
                "One minute sir, an emergency case came in. I will return immediately.",
            ],
            "near_miss": [
                "It is asking for UPI PIN. I am typing slowly because under pressure mistakes happen.",
                "It says 'Incorrect PIN'. This is making me more anxious, sir.",
                "Now it says 'Too many attempts, please wait'. These systems are very strict.",
                "I restarted the phone. It turned on, but internet feels even slower now.",
            ],
            "extract": [
                "Officer sir, please type the UPI ID in message. The text is small and I want to write it in my register to cross-check properly.",
                "Please send the UPI ID clearly in message. I will note it down like a medical record and then proceed carefully.",
            ],
            "endurance": [
                "Now it shows 'Bank server temporarily down'. Sir, I am trying, but systems are failing today.",
                "Please give me 5 minutes. I do not want to do anything blindly and create more trouble.",
                "I have the UPI ID written safely. Once server stabilizes, I will try again.",
            ],
            "ask_upi": [
                "Please type the UPI ID clearly in message so I can verify before approving anything.",
            ],
            "ask_phone": [
                "Sir, please send your official department contact number as well, for record and verification.",
            ],
            "ask_more": [
                "Sir, explain in very simple steps. I will follow carefully.",
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
        "upi_authority": {
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
    }

    base = base_hi if lang == "hi" else base_en

    # Optional external JSON file(s)
    folder = os.path.join(os.path.dirname(__file__), "playbooks")
    if os.path.isdir(folder):
        for name in os.listdir(folder):
            if not name.lower().endswith(".json"):
                continue
            path = os.path.join(folder, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    base.update(data)
            except Exception:
                continue

    return base


def _filter_recent_repeats(options: list[str], conversation: list[dict[str, str]]) -> list[str]:
    recent_user = [m["text"] for m in conversation[-8:] if m.get("sender") == "user"]
    recent_user_set = {t.strip() for t in recent_user if t and t.strip()}
    return [o for o in options if o.strip() not in recent_user_set]


def _infer_stage(*, domain: str, conversation: list[dict[str, str]], next_target: str) -> str:
    if domain != "upi_refund":
        if domain != "upi_security":
            if domain != "upi_authority":
                return "default"

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
