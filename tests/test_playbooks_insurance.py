from app.playbooks import build_reply, detect_domain


def test_detect_domain_insurance_scam() -> None:
    msg = "LIC insurance policy premium due today. Pay premium via UPI to activate policy number LIC-123."
    assert detect_domain(msg) == "insurance_scam"


def test_build_reply_insurance_scam_all_languages() -> None:
    convo = [
        {"sender": "scammer", "text": "Sir, LIC special insurance policy for your family. Limited time offer.", "timestamp": 0},
        {"sender": "user", "text": "Okay, tell me details.", "timestamp": 1},
        {"sender": "scammer", "text": "Pay first premium today via UPI to activate.", "timestamp": 2},
    ]
    for lang in ["en", "hi", "hinglish"]:
        pb = build_reply(
            domain="insurance_scam",
            next_target="phone",
            persona="default",
            conversation=convo,
            language=lang,
            verbosity="low",
        )
        assert isinstance(pb.reply, str)
        assert len(pb.reply.strip()) > 0

