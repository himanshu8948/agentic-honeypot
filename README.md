# Agentic Honeypot API
[![CI](https://github.com/himanshu8948/agentic-honeypot/actions/workflows/ci.yml/badge.svg)](https://github.com/himanshu8948/agentic-honeypot/actions/workflows/ci.yml)

## Setup
```
pip install -r requirements.txt
```

For local tests and PDF header extraction script:
```
pip install -r requirements-dev.txt
```

Create `.env` from `.env.example` and set keys.
This project uses SQLite by default via `DB_PATH`.

Optional LLM replies (Groq):
- `LLM_ENABLED=true`
- `GROQ_API_KEY=...`
- `GROQ_MODEL=llama-3.1-8b-instant`
- `LLM_TIMEOUT_MS=4000`
- `LLM_MAX_TOKENS=180`

LLM is used for reply generation only. Detection and extraction remain rule/NLP based. If the LLM fails or times out, the system falls back to the built-in playbooks. We do not use any test-specific prompts or hardcoded scenario answers.

## Run
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Test
```
python -m pytest
```

## CI Workflow
- GitHub Actions runs automatically on every push and pull request.
- Pipeline includes dependency install, import smoke check, and full pytest suite.

## Endpoints
- `POST /api/message` with `x-api-key` header
- `POST /analyze` with `x-api-key` header (alias for compatibility)
- `GET /healthz` for health checks
- `GET /health` health-check alias (compatibility)

## Runtime Hardening
- Structured JSON logs for each request (latency, route, fallback usage, circuit status)
- LLM circuit breaker with automatic rule-only fallback on repeated failures
- Request rate limiting per client/session window
- Strict validation of LLM classifier and reply payloads before use
- Deterministic sender signal policy (SMS/OTT/Email) with risk-zone mapping
- Trusted SMS header intelligence via `TRUSTED_SMS_HEADERS` or `TRUSTED_SMS_HEADERS_PATH`

## Storage
- Default DB backend is SQLite (`DB_PATH`).

## Optional Metadata Signals
`metadata` can include:
- `platform` (`sms|telecom|rcs|whatsapp|telegram|signal|ott|email`)
- `senderHeader` (e.g., `AX-HDFCBK`)
- `senderNumber`
- `inContacts` (`true|false`)

## API Request Format
Your endpoint receives:
```json
{
  "sessionId": "uuid-v4-string",
  "message": {
    "sender": "scammer",
    "text": "URGENT: Your account has been compromised...",
    "timestamp": "2025-02-11T10:30:00Z"
  },
  "conversationHistory": [
    {
      "sender": "scammer",
      "text": "Previous message...",
      "timestamp": 1739272200000
    },
    {
      "sender": "user",
      "text": "Your previous response...",
      "timestamp": 1739272215000
    }
  ],
  "metadata": {
    "channel": "SMS",
    "language": "English",
    "locale": "IN"
  }
}
```

## API Response Format
Your API must return HTTP 200 with:
```json
{
  "status": "success",
  "reply": "Your honeypot reply to the scammer"
}
```
If `reply` is missing, the evaluator may check `message` or `text`.

## Final Output Format
After the conversation ends, submit a final output with:
```json
{
  "sessionId": "abc123-session-id",
  "scamDetected": true,
  "totalMessagesExchanged": 18,
  "engagementDurationSeconds": 120,
  "extractedIntelligence": {
    "phoneNumbers": ["+91-9876543210"],
    "bankAccounts": ["1234567890123456"],
    "upiIds": ["scammer.fraud@fakebank"],
    "phishingLinks": ["http://malicious-site.com"],
    "emailAddresses": ["scammer@fake.com"],
    "caseIds": ["CASE-12345"],
    "policyNumbers": ["POL-90876"],
    "orderNumbers": ["ORD-445566"]
  },
  "agentNotes": "Short summary of scammer behavior",
  "scamType": "optional",
  "confidenceLevel": "optional"
}
```

## Compliance Notes
Acceptable:
- LLMs/AI models for conversation (optional)
- Rule-based scam detection
- NLP extraction of intel
- State tracking
- Third-party APIs

Unacceptable:
- Hardcoded responses specific to test scenarios
- Detecting or responding differently to evaluation traffic
- Pre-mapped answers based on known test data
- Any evaluation system exploitation

## Trusted SMS Header Dataset
- Default file path: `trusted_sms_headers.txt`
- Configure path via `.env`: `TRUSTED_SMS_HEADERS_PATH=./trusted_sms_headers.txt`
- Re-generate from PDF:
`python scripts/extract_sms_headers.py "C:\\path\\List_SMS_Headers.pdf" trusted_sms_headers.txt`

## Flutter App
- Flutter UI app is in `bittu_demo_app`
- See `bittu_demo_app/README.md` for local run and backend wiring
