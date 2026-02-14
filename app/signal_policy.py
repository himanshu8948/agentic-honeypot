from dataclasses import dataclass


@dataclass(frozen=True)
class SignalAssessment:
    delta: int
    reasons: list[str]


def assess_sender_signals(
    *,
    platform: str | None,
    sender_header: str | None,
    sender_number: str | None,
    in_contacts: bool | None,
    trusted_headers: set[str],
) -> SignalAssessment:
    p = (platform or "").strip().lower()
    header = normalize_sender_header(sender_header)
    number = (sender_number or "").strip()
    reasons: list[str] = []
    delta = 0

    if p in {"sms", "telecom", "rcs"}:
        if header:
            if header not in trusted_headers:
                delta += 2
                reasons.append("unknown_sms_header")
            else:
                reasons.append("trusted_sms_header")
        elif number:
            delta += 2
            reasons.append("sender_number_without_header")
        else:
            delta += 1
            reasons.append("missing_sender_identity")

        if in_contacts is False:
            delta += 1
            reasons.append("sender_not_in_contacts")
        elif in_contacts is True:
            delta = max(0, delta - 1)
            reasons.append("sender_in_contacts")
    elif p in {"whatsapp", "telegram", "signal", "ott"}:
        if in_contacts is False:
            delta += 1
            reasons.append("unknown_ott_sender")
    elif p in {"email", "mail"}:
        if not header and not number:
            delta += 1
            reasons.append("email_without_sender_identity")

    return SignalAssessment(delta=delta, reasons=reasons)


def risk_to_zone(risk: int) -> str:
    if risk >= 75:
        return "lethal"
    if risk >= 50:
        return "block_high_risk_actions"
    if risk >= 30:
        return "warn_and_confirm"
    return "observe"


def normalize_sender_header(sender_header: str | None) -> str:
    header = (sender_header or "").strip().upper()
    if not header:
        return ""
    parts = [p for p in header.split("-") if p]
    if len(parts) >= 2:
        # Common Indian telecom format: XX-HEADER or VX-HEADER.
        # Canonical trusted token is the right-most sender header part.
        header = parts[-1]
    return header
