import re
from typing import Iterable

MONEY_KEYWORDS = [
    "rupees",
    "refund",
    "loan",
    "prize",
    "discount",
    "cashback",
    "investment",
    "returns",
    "profit",
    "earning",
    "payout",
    "commission",
    "bonus",
    "reward",
]

URGENCY_KEYWORDS = [
    "urgent",
    "immediately",
    "now",
    "today",
    "expire",
    "limited",
    "last chance",
    "hurry",
    "quick",
    "fast",
    "within",
    "deadline",
    "soon",
    "asap",
    "final warning",
]

ACTION_KEYWORDS = [
    "click",
    "verify",
    "confirm",
    "send",
    "share",
    "pay",
    "install",
    "download",
    "update",
    "activate",
    "unblock",
    "claim",
    "register",
    "submit",
    "transfer",
]

PERSONAL_INFO_KEYWORDS = [
    "otp",
    "aadhaar",
    "pan",
    "bank details",
    "account number",
    "card number",
    "cvv",
    "pin",
    "password",
    "upi id",
    "ifsc",
    "routing number",
]

IMPERSONATION_KEYWORDS = [
    "hdfc",
    "icici",
    "axis",
    "sbi",
    "kotak",
    "bank of india",
    "airtel",
    "jio",
    "vi",
    "bsnl",
    "income tax",
    "gst",
    "government",
    "police",
    "court",
    "legal",
    "rbi",
]

THREAT_KEYWORDS = [
    "blocked",
    "suspended",
    "legal action",
    "police complaint",
    "arrest",
    "fraud",
    "illegal",
    "terminated",
    "cancelled",
    "deactivated",
    "freeze",
    "locked",
]

SUSPICIOUS_KEYWORDS = sorted(
    {
        # Common scam phrasing / UI cues
        "account blocked",
        "account suspended",
        "account freeze",
        "security alert",
        "customer care",
        "support team",
        "dear customer",
        "link below",
        "verify now",
        "click link",
        "update kyc",
        "update details",
        # Keyword bundles
        *MONEY_KEYWORDS,
        *URGENCY_KEYWORDS,
        *ACTION_KEYWORDS,
        *PERSONAL_INFO_KEYWORDS,
        *IMPERSONATION_KEYWORDS,
        *THREAT_KEYWORDS,
        # Broad anchors
        "bank",
        "upi",
        "kyc",
    }
)

UPI_RE = re.compile(r"[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d -]{8,}\d")
LINK_RE = re.compile(r"https?://\S+")
BANK_RE = re.compile(r"\b\d{9,18}\b")
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)
ACCOUNT_CONTEXT_RE = re.compile(r"(account\s*(number|no\.?)|bank\s*account)", re.IGNORECASE)
MONEY_RE = re.compile(r"(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d{1,2})?", re.IGNORECASE)


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
    if MONEY_RE.search(text):
        keywords.append("money_amount")
    _unique_extend(intel["suspiciousKeywords"], keywords)

    return intel


def rule_score(text: str) -> int:
    lower = text.lower()
    score = 0

    # High-signal buckets (weighted)
    if MONEY_RE.search(text) or any(k in lower for k in MONEY_KEYWORDS):
        score += 2
    if any(k in lower for k in URGENCY_KEYWORDS):
        score += 2
    if any(k in lower for k in THREAT_KEYWORDS):
        score += 2
    if any(k in lower for k in IMPERSONATION_KEYWORDS):
        score += 2
    if any(k in lower for k in ACTION_KEYWORDS):
        score += 1
    if any(k in lower for k in PERSONAL_INFO_KEYWORDS):
        score += 3
    if any(k in lower for k in ["anydesk", "teamviewer", "rustdesk", "quick support", "quicksupport", "apk"]):
        score += 3
    if LINK_RE.search(text):
        score += 2

    # Combo pattern: "send/share" + sensitive token is very high confidence
    if any(k in lower for k in ["share", "send", "provide", "submit"]) and any(
        k in lower for k in ["otp", "upi", "account", "card", "password", "pin", "cvv", "aadhaar", "pan"]
    ):
        score += 4

    # Bonus if multiple scam dimensions show up together
    dimensions = 0
    dimensions += 1 if (MONEY_RE.search(text) or any(k in lower for k in MONEY_KEYWORDS)) else 0
    dimensions += 1 if any(k in lower for k in URGENCY_KEYWORDS) else 0
    dimensions += 1 if any(k in lower for k in PERSONAL_INFO_KEYWORDS) else 0
    dimensions += 1 if any(k in lower for k in IMPERSONATION_KEYWORDS) else 0
    dimensions += 1 if any(k in lower for k in THREAT_KEYWORDS) else 0
    if dimensions >= 3:
        score += 2

    return score


def infer_sender_role(text: str) -> str:
    lower = text.lower()
    scam_signals = [
        *URGENCY_KEYWORDS,
        *ACTION_KEYWORDS,
        *PERSONAL_INFO_KEYWORDS,
        *IMPERSONATION_KEYWORDS,
        *THREAT_KEYWORDS,
        "kyc",
        "bank",
        "upi",
        "payment",
        "account will be",
        "share your",
        "send your",
    ]
    if any(s in lower for s in scam_signals) or LINK_RE.search(text) or MONEY_RE.search(text):
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
