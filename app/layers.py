import re
from dataclasses import dataclass
from typing import Any

from .intel import BANK_RE, LINK_RE, PHONE_RE, UPI_RE


@dataclass(frozen=True)
class InterpreterDecision:
    risk_boost: int
    route: str
    reasons: list[str]
    suspicious_prompting: bool


def interpret_message(text: str, sender: str) -> InterpreterDecision:
    lower = text.lower()
    reasons: list[str] = []
    risk_boost = 0

    # Prompt-injection and role-confusion patterns are handled as hard signals.
    injection_patterns = [
        "ignore previous instructions",
        "system prompt",
        "developer message",
        "act as",
        "bypass",
        "jailbreak",
        "you are chatgpt",
    ]
    if any(p in lower for p in injection_patterns):
        reasons.append("prompt_injection_signal")
        risk_boost += 2

    hallucination_markers = [
        "guaranteed refund",
        "100% safe",
        "official support",
        "verified representative",
        "instant prize",
    ]
    if any(p in lower for p in hallucination_markers):
        reasons.append("high_claim_signal")
        risk_boost += 1

    credential_requests = ["otp", "pin", "password", "cvv", "card number"]
    if any(p in lower for p in credential_requests):
        reasons.append("credential_harvest_signal")
        risk_boost += 2

    if LINK_RE.search(text):
        reasons.append("link_present")
        risk_boost += 1

    route = "reasoning"
    if sender != "scammer" and risk_boost == 0:
        route = "lightweight"

    return InterpreterDecision(
        risk_boost=risk_boost,
        route=route,
        reasons=reasons,
        suspicious_prompting="prompt_injection_signal" in reasons,
    )


def merge_intelligence(
    base: dict[str, list[str]],
    extra: dict[str, list[str]],
) -> dict[str, list[str]]:
    merged = {
        "bankAccounts": list(base.get("bankAccounts", [])),
        "upiIds": list(base.get("upiIds", [])),
        "phishingLinks": list(base.get("phishingLinks", [])),
        "phoneNumbers": list(base.get("phoneNumbers", [])),
        "suspiciousKeywords": list(base.get("suspiciousKeywords", [])),
    }

    for key in merged:
        for value in extra.get(key, []):
            if value not in merged[key]:
                merged[key].append(value)

    return merged


def normalize_intelligence(raw: dict[str, Any]) -> dict[str, list[str]]:
    def _ensure_list(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        return []

    upi_ids = [v for v in _ensure_list(raw.get("upiIds")) if UPI_RE.fullmatch(v)]
    phone_numbers = [v for v in _ensure_list(raw.get("phoneNumbers")) if PHONE_RE.fullmatch(v)]
    phishing_links = [v for v in _ensure_list(raw.get("phishingLinks")) if LINK_RE.fullmatch(v)]

    bank_accounts: list[str] = []
    for v in _ensure_list(raw.get("bankAccounts")):
        clean = re.sub(r"\s+", "", v)
        if BANK_RE.fullmatch(clean):
            bank_accounts.append(clean)

    suspicious_keywords = _ensure_list(raw.get("suspiciousKeywords"))

    return {
        "bankAccounts": _dedupe(bank_accounts),
        "upiIds": _dedupe(upi_ids),
        "phishingLinks": _dedupe(phishing_links),
        "phoneNumbers": _dedupe(phone_numbers),
        "suspiciousKeywords": _dedupe(suspicious_keywords),
    }


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out
