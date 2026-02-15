from app.playbooks import build_reply, detect_domain


def test_detect_domain_loan_scam() -> None:
    msg = "Instant loan approved. No credit check. Pay processing fee via UPI today for disbursal."
    assert detect_domain(msg) == "loan_scam"


def test_build_reply_loan_scam_all_languages() -> None:
    convo = [
        {"sender": "scammer", "text": "Sir, instant personal loan 5 lakh approved. No documents.", "timestamp": 0},
        {"sender": "user", "text": "Okay tell me details.", "timestamp": 1},
        {"sender": "scammer", "text": "Pay processing fee 2000 via UPI now then disbursal in 24 hours.", "timestamp": 2},
    ]
    for lang in ["en", "hi", "hinglish"]:
        pb = build_reply(
            domain="loan_scam",
            next_target="link",
            persona="default",
            conversation=convo,
            language=lang,
            verbosity="low",
        )
        assert isinstance(pb.reply, str)
        assert len(pb.reply.strip()) > 0

