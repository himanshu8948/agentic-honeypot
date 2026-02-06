# himanshu_agentic_honeypot

## Setup
```
pip install -r requirements.txt
```

Create `.env` from `.env.example` and set keys.

## Run
```
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Test
```
pytest
```

## Endpoint
`POST /api/message` with `x-api-key` header.
