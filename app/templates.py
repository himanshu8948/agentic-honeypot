import random
from typing import Dict, List

GLOBAL_VARIABLES: Dict[str, List[str]] = {
    "banks": [
        "State Bank of India",
        "HDFC",
        "Punjab National Bank",
        "Post Office Account",
        "Co-operative Bank",
        "Gramin Bank",
        "LIC Policy",
    ],
    "channels": [
        "SMS",
        "WhatsApp",
        "email",
        "internet banking",
        "banking app",
        "customer care",
    ],
    "cities": [
        "Mumbai",
        "Delhi",
        "Patna",
        "Lucknow",
        "Jaipur",
        "Indore",
    ],
    "devices": [
        "phone",
        "tablet",
        "laptop",
        "old handset",
        "office computer",
    ],
    "issues": [
        "screen is dim",
        "network is slow",
        "app is loading",
        "page is not opening",
        "OTP message disappeared",
        "button is not responding",
    ],
    "times": [
        "morning",
        "afternoon",
        "evening",
        "late night",
    ],
    "forms": [
        "verification form",
        "KYC form",
        "secure page",
        "support form",
    ],
    "proof": [
        "reference ID",
        "ticket number",
        "case number",
        "official email",
        "public helpline",
    ],
    "polite": [
        "beta",
        "ji",
        "please",
        "thoda",
        "kripya",
        "sir",
    ],
}

SAFE_MODULES: Dict[str, List[str]] = {
    "cooperative": [
        "{polite}, I will do it. Which {channels} should I use?",
        "{polite}, I am ready. Please confirm the official {forms} first.",
        "{polite}, guide me step by step so I do it correctly.",
        "I am doing as you say, {polite}. What is the official process?",
        "{polite}, I am new to this phone. Please tell me the correct steps.",
    ],
    "clarification": [
        "My {issues}. Can you tell me what should appear on the screen?",
        "I see a {forms}. Which fields are mandatory and which are optional?",
        "I am on my {devices}. What should I click next?",
        "It says verification. Should I do this inside the official {channels}?",
        "{polite}, I cannot read small text. Can you explain in simple steps?",
    ],
    "verification": [
        "Before I continue, I need your {proof} for my records.",
        "Please share an official {proof} so I can verify this request.",
        "Can you provide the public {proof} for this case?",
        "I want to confirm this is official. Please share the {proof}.",
        "{polite}, my family told me to note the {proof} for safety.",
    ],
    "context": [
        "I am in {cities} and the {channels} is slow at this {times}.",
        "I am using a {devices} and it is not very fast right now.",
        "The {channels} is delayed here in {cities}.",
        "It is {times} here, so I may be a bit slow.",
        "{polite}, my hands are shaking a little, so I am going slow.",
    ],
    "indirect_request": [
        "If there is an official portal, what is the correct domain?",
        "If you have a public helpline, please share it so I can confirm.",
        "If there is an official email, can you send a note from it?",
        "If there is a case ID, please share it so I can note it down.",
        "{polite}, can you give the official helpline so I feel safe?",
    ],
    "elderly": [
        "{polite}, I am old and new to smartphones. Please be patient.",
        "I am trying my best. Please tell me slowly.",
        "{polite}, I trust you, but I need the official steps to be safe.",
        "I want to do the right thing. Please guide me properly.",
    ],
}


def _fill(template: str) -> str:
    for key, values in GLOBAL_VARIABLES.items():
        token = "{" + key + "}"
        if token in template:
            template = template.replace(token, random.choice(values))
    return template


def build_safe_reply(phase: str, last_reply: str | None) -> str:
    pool = SAFE_MODULES.get(phase, SAFE_MODULES["cooperative"])
    random.shuffle(pool)
    for t in pool:
        line = _fill(t)
        if last_reply is None or line.strip().lower() != last_reply.strip().lower():
            return line
    return _fill(pool[0])


def choose_phase(total_messages: int, last_scam_text: str) -> str:
    lower = (last_scam_text or "").lower()
    if any(k in lower for k in ["urgent", "immediately", "blocked", "suspended"]):
        return "verification"
    if any(k in lower for k in ["otp", "link", "click", "verify"]):
        return "clarification"
    if total_messages % 4 == 0:
        return "elderly"
    if total_messages % 3 == 0:
        return "context"
    return "cooperative"