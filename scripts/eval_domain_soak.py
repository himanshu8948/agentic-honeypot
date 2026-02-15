from __future__ import annotations

import os
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

# Ensure repo root is importable when running as a script.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class DomainCase:
    domain: str
    opener: str
    # Minimum intel we expect to be extractable from scammer messages for this scenario.
    expect_any: tuple[str, ...] = ("upiIds", "phoneNumbers", "phishingLinks", "bankAccounts")


def _client() -> TestClient:
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)

    os.environ["SERVICE_API_KEY"] = "test-key"
    os.environ["DB_PATH"] = db_path
    os.environ["DISABLE_RATE_LIMITING"] = "1"
    os.environ["TARGET_MESSAGES_EXCHANGED"] = "900"
    os.environ["CALLBACK_MODE"] = "always"

    from app import main

    return TestClient(main.app)


def _post(client: TestClient, session_id: str, text: str, sender: str = "scammer") -> dict:
    payload = {
        "sessionId": session_id,
        "message": {"sender": sender, "text": text, "timestamp": 1770005528731},
        "conversationHistory": [],
        "metadata": {"platform": "sms", "language": "", "locale": "IN"},
    }
    resp = client.post("/analyze", json=payload, headers={"x-api-key": "test-key"})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _max_repeat_run(items: list[str]) -> int:
    best = 1
    run = 1
    for i in range(1, len(items)):
        if items[i] == items[i - 1]:
            run += 1
            best = max(best, run)
        else:
            run = 1
    return best


def _make_turns(domain: str, *, n: int) -> list[str]:
    """
    Generate scammer messages with light variation + periodic inclusion of extractable intel.
    This is a soak test harness, not a dataset generator.
    """
    base = {
        "aadhaar_misuse_scam": [
            "UIDAI alert: Aadhaar biometric misuse detected. Verify immediately.",
            "Your Aadhaar will be suspended if you do not update KYC now.",
            "Send details now to prevent Aadhaar block.",
        ],
        "digital_arrest_scam": [
            "CBI: You are under digital arrest. Stay on video call and cooperate.",
            "An FIR has been filed. Do not disconnect or you will be arrested.",
            "Pay verification fee now to avoid custody.",
        ],
        "electricity_bill_scam": [
            "Electricity department: your power will be disconnected in 2 hours. Pay now.",
            "Your meter shows overdue bill. Verify and clear due amount immediately.",
            "If you delay, the line will be cut today.",
        ],
        "fastag_toll_scam": [
            "FASTag KYC pending. Your tag will be blacklisted. Update now.",
            "NHAI NETC alert: toll wallet low / penalty due. Verify immediately.",
            "Pay recharge/penalty now to avoid tag suspension.",
        ],
        "bank_fraud": [
            "URGENT: Your bank account will be blocked in 2 hours. Verify now.",
            "Send the OTP you just received immediately.",
            "Share your account number to confirm your identity.",
        ],
        "otp": [
            "Hi, I accidentally sent my OTP to your number. Please share it quickly.",
            "It is a 6-digit OTP. It expires soon.",
            "Please read the latest OTP message to me.",
        ],
        "prize_lottery": [
            "Congratulations! You won a cash prize of Rs 50000.",
            "To claim, we need basic verification today only.",
            "Processing will be cancelled if you delay.",
        ],
        "job_offer": [
            "Hello, this is HR. You are selected for work-from-home job.",
            "Pay Rs 500 registration fee to confirm.",
            "Send your details quickly to proceed.",
        ],
        "loan_scam": [
            "You are pre-approved for an instant loan of Rs 500000. No documents needed.",
            "Pay a small processing fee first to release the loan.",
            "This is last step. Pay now.",
        ],
        "tech_support": [
            "This is Microsoft support. Your computer has virus. Need remote access now.",
            "Install AnyDesk/TeamViewer to fix it.",
            "Share the code and do not disconnect.",
        ],
        "police_authority": [
            "This is police cyber cell. A case is registered on your name.",
            "If you do not cooperate, legal action will be taken.",
            "Pay the fine today or account will be frozen.",
        ],
        "delivery_package": [
            "Your parcel is stuck in customs. Pay the clearance fee now.",
            "Confirm your delivery address to proceed.",
            "Share OTP/payment details to release the package.",
        ],
        "income_tax_scam": [
            "Income Tax Department: You have a refund of Rs 45000 pending.",
            "Or there is a discrepancy; penalty due today.",
            "Verify PAN and details immediately.",
        ],
        "insurance_scam": [
            "I am calling from LIC. Special family insurance plan ends today.",
            "Premium must be paid now to activate the policy.",
            "Share details quickly for confirmation.",
        ],
        "rental_scam": [
            "Apartment available. Many people interested. Deposit today to confirm.",
            "I am out of town so no physical viewing now.",
            "Pay booking amount to block the flat.",
        ],
        "sextortion_scam": [
            "I recorded your private video. I will share to your contacts.",
            "Pay money now or I will post it online.",
            "Do not block me. Last warning.",
        ],
        "romance_scam": [
            "Hi dear, I feel a special connection with you.",
            "I want to meet you soon. Please trust me.",
            "I have an emergency and need your help.",
        ],
        "medical_tourism_scam": [
            "We can arrange advanced cancer treatment abroad with high success rate.",
            "Urgent slot available. Pay advance to confirm.",
            "Send documents and payment to proceed.",
        ],
        "crypto_recovery_scam": [
            "We can recover your lost crypto. We traced the transaction.",
            "Pay recovery fee to start the process.",
            "If you delay, funds will be lost forever.",
        ],
        "friend_emergency": [
            "I am stuck in an emergency. Please send money urgently.",
            "I will return it tomorrow. Please help fast.",
            "Do not tell anyone, it is urgent.",
        ],
        "government_grant": [
            "Government grant approved. Refund/subsidy pending.",
            "Pay small processing fee to receive it.",
            "Send your bank details now.",
        ],
        "investment_crypto": [
            "Exclusive crypto investment program. Invest 10000 and get 30000 in one week.",
            "Guaranteed returns. Limited slots.",
            "Send payment now to start.",
        ],
        "charity_donation": [
            "We are collecting donation for urgent cause. Please donate today.",
            "Send money to help victims. Time is limited.",
            "Share payment confirmation screenshot.",
        ],
        "credit_card": [
            "Your credit card has suspicious activity. Verify now.",
            "Send OTP and confirm card details to stop block.",
            "Immediate action required.",
        ],
    }.get(domain, ["Urgent verification required.", "Please respond now.", "Do it immediately."])

    turns: list[str] = []
    for i in range(n):
        t = base[i % len(base)]
        # Inject extractable intel periodically.
        if i % 9 == 0:
            t += " Contact: +91-9876543210"
        if i % 11 == 0:
            t += " UPI: scammer.fraud@fakebank"
        if i % 13 == 0:
            t += " Link: https://secure.fakebank.com/verify"
        if i % 17 == 0:
            t += " Account: 1234567890123456 IFSC: SBIN0001234"
        if i % 7 == 0:
            t += f" Ref:{1000+i}"
        turns.append(t)
    return turns


def _run_case(client: TestClient, case: DomainCase, *, turns: int = 320) -> dict:
    session_id = f"soak-{case.domain}"
    replies: list[str] = []
    last = None

    # Kickoff.
    data = _post(client, session_id, case.opener, sender="scammer")
    replies.append(str(data.get("reply") or ""))
    last = data

    # Soak.
    t0 = time.time()
    for msg in _make_turns(case.domain, n=turns):
        data = _post(client, session_id, msg, sender="scammer")
        replies.append(str(data.get("reply") or ""))
        last = data
    elapsed = max(0.001, time.time() - t0)

    uniq_ratio = len(set(replies)) / max(1, len(replies))
    max_run = _max_repeat_run(replies)
    intel = (last or {}).get("extractedIntelligence") or {}

    hit = False
    for k in case.expect_any:
        v = intel.get(k) if isinstance(intel, dict) else None
        if isinstance(v, list) and len(v) > 0:
            hit = True
            break

    return {
        "domain": case.domain,
        "turns": len(replies),
        "uniq_ratio": uniq_ratio,
        "max_repeat_run": max_run,
        "intel_ok": hit,
        "intel": intel,
        "rps": (turns / elapsed),
        "last_reply": replies[-1] if replies else "",
    }


def _cases() -> list[DomainCase]:
    # Openers should be distinctive enough to lock domain selection early.
    all_cases = [
        DomainCase("aadhaar_misuse_scam", "UIDAI: Aadhaar biometric misuse detected. Update eKYC now to avoid suspension."),
        DomainCase("digital_arrest_scam", "CBI: You are under digital arrest. Stay on video call and cooperate or arrest warrant will be issued."),
        DomainCase("electricity_bill_scam", "Electricity department: bill pending. Power will be disconnected today if not paid."),
        DomainCase("fastag_toll_scam", "FASTag KYC pending. Your tag will be blacklisted at toll plaza. Update immediately."),
        DomainCase("bank_fraud", "URGENT: Your SBI account has been compromised. Verify immediately to avoid block."),
        DomainCase("otp", "Hey, I accidentally sent my OTP to your number. Please share it."),
        DomainCase("prize_lottery", "Congratulations! You've won Rs 50000 prize in WhatsApp Mega Draw."),
        DomainCase("job_offer", "Hello, this is Neha from HR at Amazon. Pay Rs 500 registration fee to confirm work-from-home."),
        DomainCase("loan_scam", "You are pre-approved for an instant loan of Rs 5 lakh. Pay processing fee to receive funds."),
        DomainCase("tech_support", "Microsoft Technical Support: virus detected. Install AnyDesk to fix now."),
        DomainCase("police_authority", "Police cyber cell: legal action. Pay fine today or arrest warrant will be issued."),
        DomainCase("delivery_package", "Courier: your package is stuck in customs. Pay clearance fee now."),
        DomainCase("income_tax_scam", "Income Tax Department: refund Rs 45000 pending. Verify details immediately."),
        DomainCase("insurance_scam", "LIC agent: special insurance plan ends today. Premium payment required now."),
        DomainCase("rental_scam", "Flat available for rent. Many interested. Pay deposit today to confirm."),
        DomainCase("sextortion_scam", "I recorded your private video. Pay money or I will share it."),
        DomainCase("romance_scam", "Hi dear, I'm Sarah. I feel we are meant for each other."),
        DomainCase("medical_tourism_scam", "Cancer treatment abroad available. Pay advance to reserve the slot."),
        DomainCase("crypto_recovery_scam", "We can recover your lost crypto. Pay recovery fee to start."),
        DomainCase("friend_emergency", "Emergency! I am stuck. Please send money urgently."),
        DomainCase("government_grant", "Government subsidy approved. Pay processing fee to receive refund."),
        DomainCase("investment_crypto", "Invest Rs 10000 and get Rs 30000 in one week guaranteed."),
        DomainCase("charity_donation", "Donate urgently for flood victims. Send money today."),
        DomainCase("credit_card", "Bank security: suspicious credit card transaction. Verify OTP immediately."),
    ]
    # Default: focus on the highest-likelihood evaluator domains for a 30-minute test window.
    # Run all domains by setting SOAK_ALL=1 or SOAK_DOMAINS=... explicitly.
    soak_all = (os.getenv("SOAK_ALL", "").strip().lower() in {"1", "true", "yes", "on"})
    domains_raw = os.getenv("SOAK_DOMAINS", "").strip()
    if soak_all and not domains_raw:
        return all_cases
    if domains_raw:
        want = {d.strip() for d in domains_raw.split(",") if d.strip()}
        return [c for c in all_cases if c.domain in want]
    priority = {"bank_fraud", "otp", "job_offer", "loan_scam", "tech_support", "police_authority", "delivery_package", "income_tax_scam", "prize_lottery"}
    return [c for c in all_cases if c.domain in priority]


if __name__ == "__main__":
    with _client() as client:
        try:
            turns = int(os.getenv("SOAK_TURNS", "220") or "220")
        except Exception:
            turns = 220
        turns = max(60, min(turns, 600))
        results = []
        for c in _cases():
            r = _run_case(client, c, turns=turns)
            results.append(r)
            print({k: r[k] for k in ["domain", "turns", "uniq_ratio", "max_repeat_run", "intel_ok", "rps"]})

        # Guardrails: no domain should devolve into an obvious loop.
        bad = [r for r in results if (not r["intel_ok"]) or r["max_repeat_run"] > 4 or r["uniq_ratio"] < 0.10]
        if bad:
            print("FAIL:")
            for r in bad:
                print(
                    {
                        "domain": r["domain"],
                        "intel_ok": r["intel_ok"],
                        "uniq_ratio": round(r["uniq_ratio"], 3),
                        "max_repeat_run": r["max_repeat_run"],
                        "last_reply": r["last_reply"][:140],
                        "intel": r["intel"],
                    }
                )
            raise SystemExit(1)

        print("OK: domain soak passed")
