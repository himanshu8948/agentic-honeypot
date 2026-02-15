from app.playbooks import build_reply, detect_domain


def test_detect_domain_medical_tourism_scam() -> None:
    msg = "We have an urgent slot available in Singapore hospital for cancer cure package. Pay booking amount today."
    assert detect_domain(msg) == "medical_tourism_scam"


def test_build_reply_medical_tourism_scam_all_languages() -> None:
    convo = [
        {"sender": "scammer", "text": "Sir, miracle cancer treatment package in Thailand. 95% success rate.", "timestamp": 0},
        {"sender": "user", "text": "Please help, tell me details.", "timestamp": 1},
        {"sender": "scammer", "text": "Pay booking amount now to lock your slot.", "timestamp": 2},
    ]
    for lang in ["en", "hi", "hinglish"]:
        pb = build_reply(
            domain="medical_tourism_scam",
            next_target="upi",
            persona="default",
            conversation=convo,
            language=lang,
            verbosity="low",
        )
        assert isinstance(pb.reply, str)
        assert len(pb.reply.strip()) > 0

