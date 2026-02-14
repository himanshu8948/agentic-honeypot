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
) -> PlaybookReply:
    templates = _load_templates()
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


def _load_templates() -> dict[str, Any]:
    # Built-in templates; can be overridden by JSON file in app/playbooks/*.json later.
    base = {
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
        return "default"

    # Use scammer-turn count to pace like your script (0-40+ minutes mapping).
    scammer_turns = sum(1 for m in conversation if m.get("sender") == "scammer")
    last_scam = ""
    for m in reversed(conversation):
        if m.get("sender") == "scammer":
            last_scam = str(m.get("text", "")).lower()
            break

    if scammer_turns <= 2:
        return "hook"
    if any(k in last_scam for k in ["urgent", "jaldi", "please", "job", "problem"]):
        # Push friction/urgency handling early.
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
