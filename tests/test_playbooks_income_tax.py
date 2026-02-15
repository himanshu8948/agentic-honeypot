from app.playbooks import build_reply, detect_domain


def test_detect_domain_income_tax_scam() -> None:
    msg = "Income Tax Department: refund pending for AY 2024-25. Provide bank details or pay processing fee today."
    assert detect_domain(msg) == "income_tax_scam"


def test_build_reply_income_tax_scam_all_languages() -> None:
    convo = [
        {"sender": "scammer", "text": "Income Tax officer here. You have refund pending and must verify now.", "timestamp": 0},
        {"sender": "user", "text": "Okay sir, please tell me details.", "timestamp": 1},
        {"sender": "scammer", "text": "Pay fee via UPI or share bank details for refund immediately.", "timestamp": 2},
    ]
    for lang in ["en", "hi", "hinglish"]:
        pb = build_reply(
            domain="income_tax_scam",
            next_target="phone",
            persona="default",
            conversation=convo,
            language=lang,
            verbosity="low",
        )
        assert isinstance(pb.reply, str)
        assert len(pb.reply.strip()) > 0

