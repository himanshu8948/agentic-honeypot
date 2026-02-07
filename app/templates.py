import random

SAFE_VARIANTS = {
    "greet": [
        "Sorry, I am confused. Can you explain the steps?",
        "I am not sure I understand. What should I do first?",
        "Please explain the process in simple steps.",
        "Can you tell me the exact steps to verify?",
    ],
    "otp_steps": [
        "I got an OTP, but where exactly do I enter it?",
        "I received an OTP. Which official page should I enter it on?",
        "OTP came, but I am not sure where to submit it. Please guide.",
        "Where should I type the OTP? Is there an official app or site?",
    ],
    "official_site": [
        "Please share the official website domain for this verification.",
        "Can you give the official portal link/domain?",
        "Which official site should I use? Please share the domain.",
        "Is there an official app or website for this?",
    ],
    "branch_ifsc": [
        "Which bank and branch is this for? Please share IFSC.",
        "Please confirm bank name and IFSC code.",
        "Which branch is handling this? Share IFSC and branch name.",
        "I need the branch and IFSC to verify.",
    ],
    "ref_id": [
        "Can you give a reference/ticket ID for this block?",
        "Please share the complaint/reference ID.",
        "Do you have a ticket number for this case?",
        "Share the reference number so I can note it.",
    ],
    "helpline": [
        "Please provide the official helpline number from the bank website.",
        "Can you share the public customer care number?",
        "Give the official helpline so I can verify this.",
        "Is there a public contact number I can call?",
    ],
    "alt_channel": [
        "The link shows a warning. Do you have an alternate official portal?",
        "This link seems unsafe. Is there a backup official site?",
        "Can you share a different official site or channel?",
        "The portal isn't loading. Any alternate official link?",
    ],
    "upi_request": [
        "If payment is needed, please share the exact UPI ID.",
        "Can you confirm the UPI ID to use?",
        "Please share the UPI ID and amount.",
        "Do you have a UPI ID or QR code?",
    ],
    "phone_request": [
        "If OTP must be read, please share the official number.",
        "Can you give the official phone number for verification?",
        "What is the official number I should call?",
        "Please share the official contact number.",
    ],
    "details_required": [
        "Which details are mandatory on the form?",
        "What fields should I fill and which should I skip?",
        "Please tell me the required fields only.",
        "Which details do you need exactly?",
    ],
    "confirm_identity": [
        "Please confirm your full name and department.",
        "Which team are you from?",
        "Can you confirm your designation?",
        "Please share your department name.",
    ],
    "final_verify": [
        "I want to verify this is official. Please share public proof.",
        "Please provide official verification details before I proceed.",
        "I need official verification details to proceed.",
        "Please share public verification info for this request.",
    ],
}


def choose_variants(keys: list[str], last_reply: str | None) -> str:
    # Build a large pool of safe variations without repetition
    pool: list[str] = []
    for key in keys:
        pool.extend(SAFE_VARIANTS.get(key, []))
    random.shuffle(pool)
    for line in pool:
        if last_reply is None or line.strip().lower() != last_reply.strip().lower():
            return line
    return pool[0] if pool else "Please explain the official steps again."


def build_reply_from_state(
    last_scam_text: str,
    last_reply: str | None,
    has_upi: bool,
    has_phone: bool,
    has_link: bool,
    has_bank: bool,
    total_messages: int,
) -> str:
    lower = (last_scam_text or "").lower()
    keys: list[str] = []

    if "otp" in lower:
        keys += ["otp_steps", "official_site"]
    if "account" in lower or "bank" in lower:
        keys += ["branch_ifsc", "ref_id"]
    if "link" in lower or "http" in lower:
        keys += ["alt_channel", "details_required"]

    if not has_upi:
        keys.append("upi_request")
    if not has_phone:
        keys.append("phone_request")
    if not has_bank:
        keys.append("branch_ifsc")

    if total_messages <= 3:
        keys.append("greet")
    else:
        keys.append("final_verify")

    # Ensure some identity confirmation from time to time
    if total_messages % 4 == 0:
        keys.append("confirm_identity")

    return choose_variants(keys, last_reply)