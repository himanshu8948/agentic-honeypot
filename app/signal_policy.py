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
    trusted_norm = {normalize_sender_header(h) for h in trusted_headers}
    reasons: list[str] = []
    delta = 0

    if p in {"sms", "telecom", "rcs"}:
        if header:
            if header not in trusted_norm:
                # Untrusted SMS sender headers are a strong risk signal.
                delta += 20
                reasons.append("unknown_sms_header")
            else:
                reasons.append("trusted_sms_header")
        elif number:
            delta += 10
            reasons.append("sender_number_without_header")
        else:
            delta += 5
            reasons.append("missing_sender_identity")

        if in_contacts is False:
            delta += 3
            reasons.append("sender_not_in_contacts")
        elif in_contacts is True:
            # Contacts reduce uncertainty but never override "unknown_sms_header".
            delta = max(0, delta - 3)
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
    if risk >= 80:
        return "lethal"
    if risk >= 55:
        return "block_high_risk_actions"
    if risk >= 35:
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
        return parts[-1]
    return header
