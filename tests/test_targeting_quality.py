from app.main import _ensure_engagement_question, _get_next_extraction_target


def test_next_target_case_from_authority_context() -> None:
    conversation = [{"sender": "scammer", "text": "Officer name and FIR number needed, share OTP now"}]
    intel = {
        "phoneNumbers": [],
        "upiIds": [],
        "phishingLinks": [],
        "bankAccounts": ["123456789012"],
        "emailAddresses": [],
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": [],
        "suspiciousKeywords": [],
    }
    state = {"asked": {}}
    prompt, key = _get_next_extraction_target(conversation=conversation, intel=intel, state=state, domain="bank_fraud")
    assert key == "case"
    assert "fir" in prompt.lower() or "reference" in prompt.lower()


def test_next_target_policy_for_insurance_context() -> None:
    conversation = [{"sender": "scammer", "text": "Your insurance claim is blocked, share policy details now"}]
    intel = {
        "phoneNumbers": ["+91 99999 88888"],
        "upiIds": [],
        "phishingLinks": [],
        "bankAccounts": [],
        "emailAddresses": [],
        "caseIds": [],
        "policyNumbers": [],
        "orderNumbers": [],
        "suspiciousKeywords": [],
    }
    state = {"asked": {}}
    prompt, key = _get_next_extraction_target(conversation=conversation, intel=intel, state=state, domain="insurance_scam")
    assert key in {"bank", "policy"}
    assert isinstance(prompt, str) and len(prompt) > 10


def test_ensure_engagement_question_supports_new_keys() -> None:
    out = _ensure_engagement_question("Please confirm.", "case", salt="s1")
    assert "?" in out
    out2 = _ensure_engagement_question("Please confirm.", "email", salt="s2")
    assert "?" in out2
    out3 = _ensure_engagement_question("Please confirm.", "order", salt="s3")
    assert "?" in out3


def test_ensure_engagement_question_adds_relevant_followup_when_irrelevant_question_exists() -> None:
    out = _ensure_engagement_question("I am confused, what next?", "upi", salt="s4")
    low = out.lower()
    assert "?" in out
    assert "upi" in low or "handle" in low
