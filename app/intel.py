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

DEVANAGARI_KEYWORDS = [
    # Common Hindi-script scam markers (Devanagari).
    # Used for pure-Hindi and mixed-script scam detection.
    "खाता",  # ????
    "अकाउंट",  # ??????
    "खाता नंबर",  # ???? ????
    "खाता संख्या",  # ???? ??????
    "बैंक",  # ????
    "ओटीपी",  # ?????
    "पिन",  # ???
    "पासवर्ड",  # ???????
    "यूपीआई",  # ??????
    "भुगतान",  # ??????
    "पेमेंट",  # ??????
    "ट्रांसफर",  # ????????
    "लिंक",  # ????
    "क्लिक",  # ?????
    "वेरिफाई",  # ???????
    "सत्यापित",  # ????????
    "केवाईसी",  # ???????
    "आधार",  # ????
    "पैन",  # ???
    "ब्लॉक",  # ?????
    "सस्पेंड",  # ???????
    "फ्रीज",  # ?????
    "लॉक",  # ???
    "तुरंत",  # ?????
    "अभी",  # ???
    "जल्दी",  # ?????
    "पुलिस",  # ?????
    "कानूनी",  # ??????
    "गिरफ्तार",  # ????????
    "आयकर",  # ????
    "इनकम टैक्स",  # ???? ?????
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

TECH_SUPPORT_OPENERS = [
    "from support",
    "from microsoft support",
    "from windows support",
    "technical support",
    "device has malware",
    "device has virus",
    "we detected security breach",
    "security breach",
    "share remote access code",
    "remote access code",
]

SIM_SWAP_OPENERS = [
    "sim card replacement",
    "sim replacement",
    "sim swap",
    "sim will be deactivated",
    "sim will be blocked",
    "upgrade to 5g sim",
    "your sim will stop",
]

ECOMMERCE_OPENERS = [
    "your order",
    "order confirmation",
    "delivery",
    "courier",
    "parcel",
    "shipment",
    "tracking",
    "customs",
]

CHARITY_OPENERS = [
    "donate",
    "donation",
    "charity",
    "fundraiser",
    "relief fund",
]

FRIEND_DISTRESS_OPENERS = [
    "i am in trouble",
    "need urgent money",
    "send money urgently",
    "i lost my phone",
    "new number",
    "this is my new number",
]

TAX_REFUND_OPENERS = [
    "income tax refund",
    "tax refund",
    "gst refund",
    "itr refund",
    "refund from income tax",
]

PHISHING_OPENERS = [
    "account is at risk",
    "click here to verify",
    "account will be suspended",
    "verify your details immediately",
    "security alert for your account",
]

FAKE_REFUND_OPENERS = [
    "eligible for",
    "refund is pending",
    "your refund of",
    "get cashback",
    "claim your discount",
    "unclaimed refund",
]

FAKE_LOAN_OPENERS = [
    "pre-approved for",
    "instant loan of",
    "loan approved",
    "loan application approved",
    "no document loan",
    "loan available",
    "get loan in",
]

OTP_WHATSAPP_HACK_OPENERS = [
    "i accidentally sent my otp",
    "sent you otp by mistake",
    "can you send me the code i sent you",
    "wrong number, please share the otp",
]

PRIZE_LOTTERY_OPENERS = [
    "whatsapp mega draw",
    "lucky draw",
    "winner of",
    "lottery",
    "cash prize",
    "you've won",
    "you won",
]

FAKE_JOB_OPENERS = [
    "from hr at",
    "been shortlisted",
    "shortlisted for remote",
    "remote role",
    "work from home",
    "work-from-home",
    "opportunity",
    "registration fee",
    "joining fee",
    "selected for",
]

CRYPTO_INVEST_OPENERS = [
    "crypto investment",
    "limited slots",
    "guaranteed returns",
    "double your money",
    "exclusive trading opportunity",
    "trading opportunity",
    "invest",
    "returns of",
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
        *PHISHING_OPENERS,
        *FAKE_REFUND_OPENERS,
        *FAKE_LOAN_OPENERS,
        *OTP_WHATSAPP_HACK_OPENERS,
        *PRIZE_LOTTERY_OPENERS,
        *FAKE_JOB_OPENERS,
        *CRYPTO_INVEST_OPENERS,
        *TECH_SUPPORT_OPENERS,
        *SIM_SWAP_OPENERS,
        *ECOMMERCE_OPENERS,
        *CHARITY_OPENERS,
        *FRIEND_DISTRESS_OPENERS,
        *TAX_REFUND_OPENERS,
        # Keyword bundles
        *MONEY_KEYWORDS,
        *URGENCY_KEYWORDS,
        *ACTION_KEYWORDS,
        *PERSONAL_INFO_KEYWORDS,
        *IMPERSONATION_KEYWORDS,
        *THREAT_KEYWORDS,
        *DEVANAGARI_KEYWORDS,
        # Broad anchors
        "bank",
        "upi",
        "kyc",
    }
)

UPI_RE = re.compile(r"[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"\+?\d[\d -]{8,}\d")
LINK_RE = re.compile(r"https?://\S+")
# Catch common phishing links that omit scheme, e.g. "bankverify.example.com/login"
BARE_LINK_RE = re.compile(
    r"\b(?:www\.)?[a-zA-Z0-9-]{2,}(?:\.[a-zA-Z0-9-]{2,}){1,3}(?:/[^\s]*)?\b"
)
BANK_RE = re.compile(r"\b\d{9,18}\b")
EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b")
IFSC_RE = re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b", re.IGNORECASE)
ACCOUNT_CONTEXT_RE = re.compile(r"(account\s*(number|no\.?)|bank\s*account)", re.IGNORECASE)
MONEY_RE = re.compile(r"(?:₹|rs\.?|inr)\s*[\d,]+(?:\.\d{1,2})?", re.IGNORECASE)

POLICY_NUMBER_RE = re.compile(
    r"\b(?:policy(?:\s*(?:number|no\.?))?|pol)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,24})\b",
    re.IGNORECASE,
)
ORDER_NUMBER_RE = re.compile(
    r"\b(?:order(?:\s*(?:id|number|no\.?))?|ord|awb|tracking|track|shipment|ship)\s*[:#-]?\s*([A-Z0-9][A-Z0-9-]{3,24})\b",
    re.IGNORECASE,
)

DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
GUJARATI_RE = re.compile(r"[\u0A80-\u0AFF]")


def _unique_extend(target: list[str], values: Iterable[str]) -> None:
    for v in values:
        if v not in target:
            target.append(v)


def extract_intel(text: str, intel: dict[str, list[str]]) -> dict[str, list[str]]:
    # Ensure required keys exist
    for key in [
        "bankAccounts",
        "upiIds",
        "phishingLinks",
        "phoneNumbers",
        "emailAddresses",
        "caseIds",
        "policyNumbers",
        "orderNumbers",
        "suspiciousKeywords",
    ]:
        if key not in intel:
            intel[key] = []
    lower = text.lower()

    upis = UPI_RE.findall(text)
    phones = [p for p in PHONE_RE.findall(text) if len(re.sub(r"\D", "", p)) <= 13]
    links = LINK_RE.findall(text)
    bare_links = []
    for m in BARE_LINK_RE.findall(text):
        if "." not in m or "@" in m:
            continue
        clean = m.rstrip(".,);:!?")
        if clean:
            bare_links.append(clean)
    emails = EMAIL_RE.findall(text)
    case_ids = [
        f"{prefix.upper()}{suffix.upper()}"
        for prefix, suffix in re.findall(
            r"\b(FIR|CASE|REF|REFERENCE|TICKET|COMPLAINT)[\s:#-]*([A-Z0-9-]{3,24})\b",
            text,
            flags=re.IGNORECASE,
        )
    ]
    policy_numbers = []
    for token in POLICY_NUMBER_RE.findall(text):
        normalized = token.upper().replace("-", "").replace("_", "")
        if not normalized.startswith("POL"):
            normalized = f"POL{normalized}"
        policy_numbers.append(normalized)
    order_numbers = []
    for token in ORDER_NUMBER_RE.findall(text):
        normalized = token.upper().replace("-", "").replace("_", "")
        if not normalized.startswith(("ORD", "ORDER", "AWB", "TRACK", "SHIP")):
            normalized = f"ORD{normalized}"
        order_numbers.append(normalized)
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
    # Keep bare links as seen by scammer text (no forced scheme rewrite).
    _unique_extend(intel["phishingLinks"], bare_links)
    _unique_extend(intel["emailAddresses"], emails)
    _unique_extend(intel["caseIds"], case_ids)
    _unique_extend(intel["policyNumbers"], policy_numbers)
    _unique_extend(intel["orderNumbers"], order_numbers)

    keywords = [k for k in SUSPICIOUS_KEYWORDS if k in lower]
    if MONEY_RE.search(text):
        keywords.append("money_amount")
    _unique_extend(intel["suspiciousKeywords"], keywords)

    return intel


def rule_score(text: str) -> int:
    lower = text.lower()
    score = 0

    # High-signal buckets (weighted)
    if any(p in lower for p in PHISHING_OPENERS):
        score += 3
    # Common refund/cashback hooks: keyword + amount is very high confidence.
    if any(p in lower for p in FAKE_REFUND_OPENERS) and (MONEY_RE.search(text) or any(k in lower for k in ["refund", "cashback", "discount"])):
        score += 4
    # Loan hooks: opener + amount or fee strongly indicates scam.
    if any(p in lower for p in FAKE_LOAN_OPENERS) and (MONEY_RE.search(text) or "fee" in lower or "processing" in lower):
        score += 4
    # OTP / WhatsApp takeover hooks: exact phrasing is very high confidence.
    if any(p in lower for p in OTP_WHATSAPP_HACK_OPENERS):
        score += 5
    # Lottery/prize hooks: opener + amount implies scam.
    if any(p in lower for p in PRIZE_LOTTERY_OPENERS) and (MONEY_RE.search(text) or any(k in lower for k in ["prize", "lottery", "reward"])):
        score += 4
    # Fake job offer hooks: fee + job phrases.
    if any(p in lower for p in FAKE_JOB_OPENERS) and (MONEY_RE.search(text) or "fee" in lower):
        score += 4
    # Crypto/investment hooks: invest/returns + amount/percentage/timeframe.
    if any(p in lower for p in CRYPTO_INVEST_OPENERS) and (
        MONEY_RE.search(text) or "%" in text or any(t in lower for t in ["week", "weeks", "days", "day", "month", "months"])
    ):
        score += 4
    # Tech support scams: malware/virus + remote tool / access code.
    if any(p in lower for p in TECH_SUPPORT_OPENERS) and any(
        k in lower for k in ["anydesk", "teamviewer", "rustdesk", "remote", "access code"]
    ):
        score += 5
    # SIM swap / replacement: SIM deactivation + OTP/social engineering.
    if any(p in lower for p in SIM_SWAP_OPENERS) and any(k in lower for k in ["otp", "verification code", "one time password"]):
        score += 5
    # E-commerce delivery/refund: parcel/order + link/otp/payment.
    if any(p in lower for p in ECOMMERCE_OPENERS) and (
        LINK_RE.search(text) or any(k in lower for k in ["otp", "pay", "upi", "refund"])
    ):
        score += 4
    # Charity/donation: donation ask + payment handle/link.
    if any(p in lower for p in CHARITY_OPENERS) and (any(k in lower for k in ["upi", "pay", "donate now"]) or LINK_RE.search(text)):
        score += 4
    # Friend-in-distress: impersonation + urgent money transfer.
    if any(p in lower for p in FRIEND_DISTRESS_OPENERS) and any(k in lower for k in ["send", "transfer", "upi", "urgent"]):
        score += 4
    # Tax refund: refund + link/verification request.
    if any(p in lower for p in TAX_REFUND_OPENERS) and (LINK_RE.search(text) or any(k in lower for k in ["verify", "otp", "bank details"])):
        score += 4
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

    # Hindi-script high-signal indicators (for pure Hindi / mixed script attacks).
    if any(k in text for k in ["\u0913\u091f\u0940\u092a\u0940", "OTP"]):  # ?????
        score += 3
    if any(
        k in text
        for k in [
            "\u092c\u094d\u0932\u0949\u0915",  # ?????
            "\u092b\u094d\u0930\u0940\u091c",  # ?????
            "\u0932\u0949\u0915",  # ???
            "\u0938\u0938\u094d\u092a\u0947\u0902\u0921",  # ???????
        ]
    ):
        score += 2
    if any(
        k in text
        for k in [
            "\u092f\u0942\u092a\u0940\u0906\u0908",  # ??????
            "\u092d\u0941\u0917\u0924\u093e\u0928",  # ??????
            "\u092a\u0947\u092e\u0947\u0902\u091f",  # ??????
            "\u091f\u094d\u0930\u093e\u0902\u0938\u092b\u0930",  # ????????
        ]
    ):
        score += 2
    if any(
        k in text
        for k in [
            "\u0932\u093f\u0902\u0915",  # ????
            "\u0915\u094d\u0932\u093f\u0915",  # ?????
            "\u0915\u0947\u0935\u093e\u0908\u0938\u0940",  # ???????
            "\u0906\u0927\u093e\u0930",  # ????
            "\u092a\u0948\u0928",  # ???
            "\u0906\u092f\u0915\u0930",  # ????
            "\u0907\u0928\u0915\u092e \u091f\u0948\u0915\u094d\u0938",  # ???? ?????
        ]
    ):
        score += 2
    if any(k in text for k in ["\u0924\u0941\u0930\u0902\u0924", "\u0905\u092d\u0940", "\u091c\u0932\u094d\u0926\u0940"]):
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
    # Pure-Hindi / Devanagari scam messages should still be classified as scammer.
    if DEVANAGARI_RE.search(text):
        if any(k in text for k in DEVANAGARI_KEYWORDS) or any(
            k in text
            for k in [
                "\u0916\u093e\u0924\u093e",  # ????
                "\u092c\u0948\u0902\u0915",  # ????
                "\u0913\u091f\u0940\u092a\u0940",  # ?????
                "\u092f\u0942\u092a\u0940\u0906\u0908",  # ??????
                "\u092c\u094d\u0932\u0949\u0915",  # ?????
                "\u0932\u093f\u0902\u0915",  # ????
            ]
        ):
            return "scammer"
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
