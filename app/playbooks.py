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
