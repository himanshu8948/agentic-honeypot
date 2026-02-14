# Bittu Agentic AI Flutter App

This app is a live "Agentic AI" client for the backend in this repository.

## Features implemented
- Bittu Thought-Trace terminal (THOUGHT/ACTION/TOOL_CALL/VERDICT)
- Risk Radar gauge with animated pulse
- Heist Timeline sequence panel
- Active Defense mode toggle with "Scammer Time Wasted"
- Asset Shield cards with alert flashing
- WhatsApp-style judge chat panel
- Quick scenario buttons (OTP / UPI / Hi Mom)
- Backend status check via `/health`

## Backend contract used
- `POST /analyze` with `x-api-key`
- Request body fields:
  - `sessionId`
  - `message`
  - `conversationHistory`
  - `metadata`
- `GET /health` for online status

## Local run
1. Install Flutter SDK and run:
```bash
flutter doctor
```
2. Open this folder:
```bash
cd bittu_demo_app
```
3. Install packages:
```bash
flutter pub get
```
4. Run backend in repo root:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
5. Run Flutter Windows app:
```bash
flutter run -d windows
```

## Base URLs
- Windows local backend: `http://127.0.0.1:8000`
- Android emulator backend: `http://10.0.2.2:8000`
- Render deployed backend: `https://himanshu-agentic-honeypot.onrender.com`

## Render health check
In Render, set Health Check Path to:
- `/health`

Do not use full URL in Render health check path.
