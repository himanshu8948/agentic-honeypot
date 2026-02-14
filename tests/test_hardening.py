from app.hardening import CircuitBreaker, validate_agent_result, validate_llm_result


def test_validate_llm_result_coerces_types():
    out = validate_llm_result(
        {
            "scamDetected": 1,
            "confidence": "1.7",
            "reasons": "bad",
            "intentCategory": "unknown",
        }
    )
    assert out["scamDetected"] is True
    assert out["confidence"] == 1.0
    assert out["reasons"] == []
    assert out["intentCategory"] == "other"


def test_validate_agent_result_fallbacks():
    out = validate_agent_result({}, "fallback", "notes")
    assert out["reply"] == "fallback"
    assert out["agentNotes"] == "notes"
    assert out["stopReason"] is None


def test_circuit_breaker_opens_after_threshold():
    c = CircuitBreaker(failure_threshold=2, recovery_seconds=10)
    assert c.allow_request() is True
    c.record_failure()
    assert c.allow_request() is True
    c.record_failure()
    assert c.allow_request() is False
