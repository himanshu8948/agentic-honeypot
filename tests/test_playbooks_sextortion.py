from app.playbooks import build_reply, detect_domain


def test_detect_domain_sextortion_scam() -> None:
    msg = "I recorded your private video call. Pay 50000 rupees via UPI or I will share to your contacts on Instagram."
    assert detect_domain(msg) == "sextortion_scam"


def test_build_reply_sextortion_scam_all_languages() -> None:
    convo = [
        {"sender": "scammer", "text": "I have recorded you on video call. Pay money or I will share to your contacts.", "timestamp": 0},
        {"sender": "user", "text": "Please don't do that.", "timestamp": 1},
        {"sender": "scammer", "text": "Send 50000 now via UPI, last warning.", "timestamp": 2},
    ]
    for lang in ["en", "hi", "hinglish"]:
        pb = build_reply(
            domain="sextortion_scam",
            next_target="phone",
            persona="default",
            conversation=convo,
            language=lang,
            verbosity="low",
        )
        assert isinstance(pb.reply, str)
        assert len(pb.reply.strip()) > 0

