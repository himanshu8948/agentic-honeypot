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
    asked: set[str],
) -> PlaybookReply:
    templates = _load_templates()
    domain_bank = templates.get(domain, templates["generic"])

    # Choose a template bucket based on target keywords.
    target_lower = next_target.lower()
    if "upi" in target_lower:
        bucket = "ask_upi"
    elif "phone" in target_lower or "contact" in target_lower:
        bucket = "ask_phone"
    elif "ifsc" in target_lower or "branch" in target_lower or "account" in target_lower:
        bucket = "ask_bank"
    elif "link" in target_lower:
        bucket = "ask_link"
    else:
        bucket = "ask_more"

    options = domain_bank.get(bucket, []) + templates["generic"].get(bucket, [])
    options = [o for o in options if o not in asked]
    if not options:
        options = domain_bank.get(bucket, []) or templates["generic"].get(bucket, []) or ["Okay, please share the details."]

    reply = random.choice(options)
    asked.add(reply)
    reply = _apply_persona(reply, persona)

    return PlaybookReply(
        reply=reply,
        agent_notes=f"Playbook:{domain}; target:{next_target}",
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

