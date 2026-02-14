# Agentic Honeypot API

## Setup
```
pip install -r requirements.txt
```

Create `.env` from `.env.example` and set keys.
Use a single Groq key via `GROQ_API_KEY`.
For local fallback, enable Ollama with `LOCAL_LLM_ENABLED=true` and set `OLLAMA_MODEL=qwen2.5:3b`.
For Firestore persistence, set `FIREBASE_ENABLED=true` and configure Firebase credentials.

## Run
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Test
```
pytest
```

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

## Firebase (Firestore) Storage
- Default DB backend is SQLite (`DB_PATH`).
- To use Firestore instead:
  - `FIREBASE_ENABLED=true`
  - `FIREBASE_PROJECT_ID=<your-project-id>`
  - one of:
    - `FIREBASE_CREDENTIALS_PATH=/path/to/service-account.json`
    - `FIREBASE_SERVICE_ACCOUNT_JSON=<single-line-json>`
  - Optional: `FIREBASE_APP_NAME=agentic-honeypot`
- If Firestore is enabled, session/message/intelligence data is written to Firestore collections:
  - `sessions`
  - `messages`
  - `intel`
  - `user_intel`

## Optional Metadata Signals
`metadata` can include:
- `platform` (`sms|telecom|rcs|whatsapp|telegram|signal|ott|email`)
- `senderHeader` (e.g., `AX-HDFCBK`)
- `senderNumber`
- `inContacts` (`true|false`)

## Trusted SMS Header Dataset
- Default file path: `trusted_sms_headers.txt`
- Configure path via `.env`: `TRUSTED_SMS_HEADERS_PATH=./trusted_sms_headers.txt`
- Re-generate from PDF:
`python scripts/extract_sms_headers.py "C:\\path\\List_SMS_Headers.pdf" trusted_sms_headers.txt`

## Flutter App
- Flutter UI app is in `bittu_demo_app`
- See `bittu_demo_app/README.md` for local run and backend wiring
