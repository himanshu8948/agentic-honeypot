import re
from typing import Iterable

SUSPICIOUS_KEYWORDS = [
    "urgent",
    "verify",
    "account blocked",
    "account suspended",
    "otp",
    "upi",
    "bank",
    "kyc",
    "refund",
    "limited time",
    "click link",
    "verify now",
    "win",
    "gift",
    "prize",
    "loan approved",
    "account freeze",
    "immediately",
    "pay now",
    "pay immediately",
    "dear customer",
    "your account",
    "link below",
    "customer care",
    "support team",
    "suspend",
    "security alert",
    "chargeback",
    "transaction failed",
    "reactivate",
    "update kyc",
    "update details",
]

UPI_RE = re.compile(r"[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d -]{8,}\d")
LINK_RE = re.compile(r"https?://\S+")
BANK_RE = re.compile(r"\b\d{9,18}\b")
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)
ACCOUNT_CONTEXT_RE = re.compile(r"(account\s*(number|no\.?)|bank\s*account)", re.IGNORECASE)


def _unique_extend(target: list[str], values: Iterable[str]) -> None:
    for v in values:
        if v not in target:
            target.append(v)


def extract_intel(text: str, intel: dict[str, list[str]]) -> dict[str, list[str]]:
    # Ensure required keys exist
    for key in ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "suspiciousKeywords"]:
        if key not in intel:
            intel[key] = []
    lower = text.lower()

    upis = UPI_RE.findall(text)
    phones = [p for p in PHONE_RE.findall(text) if len(re.sub(r"\D", "", p)) <= 13]
    links = LINK_RE.findall(text)
    bank_candidates = BANK_RE.findall(text)
    # Avoid treating common 10-digit phone numbers as bank accounts
    filtered_bank: list[str] = []
    for cand in bank_candidates:
        digits = re.sub(r"\D", "", cand)
        if len(digits) == 10 and digits.startswith(("6", "7", "8", "9")):
            continue
        filtered_bank.append(cand)

    if filtered_bank and (ACCOUNT_CONTEXT_RE.search(text) or IFSC_RE.search(text)):
        _unique_extend(intel["bankAccounts"], filtered_bank)

    _unique_extend(intel["upiIds"], upis)
    _unique_extend(intel["phoneNumbers"], phones)
    _unique_extend(intel["phishingLinks"], links)

    keywords = [k for k in SUSPICIOUS_KEYWORDS if k in lower]
    _unique_extend(intel["suspiciousKeywords"], keywords)

    return intel


def rule_score(text: str) -> int:
    lower = text.lower()
    score = 0

    if any(k in lower for k in ["urgent", "immediately", "now", "today"]):
        score += 1
    if any(k in lower for k in ["verify", "kyc", "otp"]):
        score += 1
    if any(k in lower for k in ["upi", "bank", "account", "payment", "transfer"]):
        score += 1
    if any(k in lower for k in ["suspend", "blocked", "freeze", "security alert"]):
        score += 1
    if LINK_RE.search(text):
        score += 1
    if any(k in lower for k in ["blocked", "suspended", "freeze"]):
        score += 1
    if any(k in lower for k in ["prize", "gift", "lottery", "offer"]):
        score += 1
    if any(k in lower for k in ["customer care", "support team", "dear customer"]):
        score += 1
    if any(k in lower for k in ["share", "send", "provide", "submit"]) and any(
        k in lower for k in ["otp", "upi", "account", "card", "password", "pin"]
    ):
        score += 2

    return score


def infer_sender_role(text: str) -> str:
    lower = text.lower()
    scam_signals = [
        "verify",
        "otp",
        "kyc",
        "blocked",
        "suspended",
        "freeze",
        "bank",
        "upi",
        "payment",
        "click link",
        "verify now",
        "urgent",
        "dear customer",
        "customer care",
        "support team",
        "account will be",
        "share your",
        "send your",
    ]
    if any(s in lower for s in scam_signals) or LINK_RE.search(text):
        return "scammer"
    return "user"


def intent_signal_score(text: str) -> int:
    lower = text.lower()
    score = 0

    urgency = ["urgent", "immediately", "now", "today", "within 1 hour", "final warning"]
    authority = ["bank", "customer care", "support team", "official", "security team"]
    threat = ["blocked", "suspended", "freeze", "legal action", "account will be closed"]
    credential = ["otp", "password", "pin", "cvv", "card number", "upi id"]
    reward = ["prize", "gift", "reward", "cashback", "offer"]
    action = ["click", "open link", "share", "send", "submit", "verify", "update kyc"]

    if any(k in lower for k in urgency):
        score += 1
    if any(k in lower for k in authority):
        score += 1
    if any(k in lower for k in threat):
        score += 2
    if any(k in lower for k in credential):
        score += 2
    if any(k in lower for k in reward):
        score += 1
    if any(k in lower for k in action):
        score += 1

    if ("otp" in lower or "pin" in lower or "password" in lower) and any(
        k in lower for k in ["share", "send", "provide", "submit"]
    ):
        score += 2

    return score
