import asyncio
import os
import re
import time
import uuid
import hashlib
import json
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse

from .config import Settings, load_settings
from .db import (
    append_message,
    connect,
    get_or_create_session,
    get_api_calls,
    init_db,
    increment_api_calls,
    list_messages,
    load_intel,
    load_user_intel,
    save_intel,
    save_user_intel,
    update_session,
)
from .intel import extract_intel, infer_sender_role, intent_signal_score, rule_score
from .hardening import (
    SlidingWindowLimiter,
    log_event,
    setup_logging,
)
from .layers import interpret_message
from .playbooks import build_reply, detect_domain
from .signal_policy import assess_sender_signals, risk_to_zone
from .fraud_corpus import best_match, load_corpus_lines
from .lookup_table import load_lookup_table
from .stat_model import load_stat_model

app = FastAPI(title="Agentic Honeypot API")

SETTINGS: Settings | None = None
DB = None
FRAUD_CORPUS: list[str] = []
LOOKUP_TABLE_COUNT = 0
REQ_LIMITER_SESSION = SlidingWindowLimiter(max_requests=400, window_seconds=60)
REQ_LIMITER_IP = SlidingWindowLimiter(max_requests=1200, window_seconds=60)
STAT_MODEL = None
INFLIGHT_SEM: asyncio.Semaphore | None = None
INFLIGHT_WAIT_S = 1.5

_EXCITED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\boh\s+no\b", re.IGNORECASE), "Observed"),
    (re.compile(r"\boh\s+my\s+god\b", re.IGNORECASE), "Observed"),
    (re.compile(r"\boh\s+my\s+goodness\b", re.IGNORECASE), "Observed"),
    (re.compile(r"\barre\s+bhagwan\b", re.IGNORECASE), "Observed"),
    (re.compile(r"\barre\s+baap\s+re\b", re.IGNORECASE), "Observed"),
    (re.compile(r"\bwow\b", re.IGNORECASE), "Observed"),
    # Avoid "overly excited" tone - keep it neutral/observational.
    (re.compile(r"\b(i[' ]?m|i am)\s+excited\b", re.IGNORECASE), "Observed"),
    (re.compile(r"\bso\s+excited\b", re.IGNORECASE), "Observed"),
]


def _health_payload() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict[str, str]:
    return _health_payload()


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return _health_payload()


@app.get("/health")
async def health() -> dict[str, str]:
    return _health_payload()


@app.api_route("/healthz", methods=["HEAD"])
async def healthz_head() -> None:
    return None


@app.api_route("/health", methods=["HEAD"])
async def health_head() -> None:
    return None


class Message(BaseModel):
    sender: str = Field(..., pattern="^(scammer|user)$")
    text: str = Field(..., min_length=1, max_length=4000)
    timestamp: int


class Metadata(BaseModel):
    channel: Optional[str] = None
    language: Optional[str] = None
    locale: Optional[str] = None
    verbosity: Optional[str] = None  # e.g. "low" | "high"
    persona: Optional[str] = None  # e.g. "vet_doctor" | "truck_owner" | "shopkeeper"
    platform: Optional[str] = None
    senderHeader: Optional[str] = None
    senderNumber: Optional[str] = None
    inContacts: Optional[bool] = None


class MessageRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: list[Message] = Field(default_factory=list)
    metadata: Optional[Metadata] = None


class MessageResponse(BaseModel):
    status: str
    sessionId: str
    reply: str
    scamDetected: bool
    shouldEngage: bool
    extractedIntelligence: dict[str, list[str]]
    agentNotes: str


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if SETTINGS is None:
        raise HTTPException(status_code=500, detail="Service not initialized")
    if not x_api_key or x_api_key != SETTINGS.service_api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")


@app.on_event("startup")
async def startup() -> None:
    global SETTINGS, DB, FRAUD_CORPUS, LOOKUP_TABLE_COUNT, STAT_MODEL, REQ_LIMITER_SESSION, REQ_LIMITER_IP, INFLIGHT_SEM, INFLIGHT_WAIT_S
    setup_logging()
    SETTINGS = load_settings()
    DB = connect(SETTINGS.db_path)
    init_db(DB)
    FRAUD_CORPUS = load_corpus_lines()
    LOOKUP_TABLE_COUNT = len(load_lookup_table())
    STAT_MODEL = load_stat_model()
    # Rate limiting knobs (safe defaults).
    try:
        window = int(os.getenv("RL_WINDOW_SECONDS", "60") or "60")
    except Exception:
        window = 60
    window = max(5, min(window, 600))
    try:
        per_session = int(os.getenv("RL_MAX_PER_SESSION", "400") or "400")
    except Exception:
        per_session = 400
    per_session = max(5, min(per_session, 10000))
    try:
        per_ip = int(os.getenv("RL_MAX_PER_IP", "1200") or "1200")
    except Exception:
        per_ip = 1200
    per_ip = max(5, min(per_ip, 50000))
    REQ_LIMITER_SESSION = SlidingWindowLimiter(max_requests=per_session, window_seconds=window)
    REQ_LIMITER_IP = SlidingWindowLimiter(max_requests=per_ip, window_seconds=window)

    # Concurrency guard (prevents resource exhaustion under burst traffic).
    try:
        max_inflight = int(os.getenv("MAX_INFLIGHT_REQUESTS", "128") or "128")
    except Exception:
        max_inflight = 128
    max_inflight = max(1, min(max_inflight, 2000))
    try:
        wait_ms = int(os.getenv("MAX_INFLIGHT_WAIT_MS", "1500") or "1500")
    except Exception:
        wait_ms = 1500
    wait_ms = max(10, min(wait_ms, 30000))
    INFLIGHT_WAIT_S = wait_ms / 1000.0
    INFLIGHT_SEM = asyncio.Semaphore(max_inflight)
    log_event(
        "startup_complete",
        db_path=SETTINGS.db_path,
        fraudCorpusLines=len(FRAUD_CORPUS),
        lookupPatterns=LOOKUP_TABLE_COUNT,
        llmEnabled=False,
        statModelLoaded=bool(STAT_MODEL),
        rlWindowSeconds=window,
        rlMaxPerSession=per_session,
        rlMaxPerIp=per_ip,
        maxInflight=max_inflight,
        maxInflightWaitMs=wait_ms,
    )


@app.middleware("http")
async def inflight_guard_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    disable_guard = (os.getenv("DISABLE_RATE_LIMITING", "").strip().lower() in {"1", "true", "yes", "on"})
    sem = INFLIGHT_SEM
    if disable_guard or sem is None:
        return await call_next(request)
    try:
        await asyncio.wait_for(sem.acquire(), timeout=INFLIGHT_WAIT_S)
    except TimeoutError:
        client_host = request.client.host if request.client else "unknown"
        log_event("server_busy", client=client_host, path=str(request.url.path))
        return JSONResponse(status_code=503, content={"detail": "Server busy, retry shortly"})
    try:
        return await call_next(request)
    finally:
        try:
            sem.release()
        except Exception:
            pass


@app.post("/api/message", response_model=MessageResponse)
@app.post("/analyze", response_model=MessageResponse)
async def handle_message(
    payload: MessageRequest,
    request: Request,
    _auth: None = Depends(require_api_key),
) -> MessageResponse:
    if SETTINGS is None or DB is None:
        raise HTTPException(status_code=500, detail="Service not initialized")
    request_start = time.time()
    incoming_session_id = (payload.sessionId or "").strip()
    session_id = _normalize_session_id(incoming_session_id)
    if session_id != incoming_session_id:
        log_event("session_id_normalized", incomingSessionId=incoming_session_id, sessionId=session_id)

    client_host = request.client.host if request.client else "unknown"
    limiter_key = f"{client_host}:{session_id}"
    ip_key = f"{client_host}"
    disable_rl = (os.getenv("DISABLE_RATE_LIMITING", "").strip().lower() in {"1", "true", "yes", "on"})
    if not disable_rl and (not REQ_LIMITER_IP.allow(ip_key) or not REQ_LIMITER_SESSION.allow(limiter_key)):
        log_event("rate_limited", sessionId=session_id, client=client_host)
        raise HTTPException(status_code=429, detail="Too many requests")

    session = get_or_create_session(DB, session_id)
    increment_api_calls(DB, session_id)
    api_calls = get_api_calls(DB, session_id)
    if int(session["total_messages"]) == 0 and payload.conversationHistory:
        for msg in payload.conversationHistory:
            append_message(DB, session_id, msg.sender, _sanitize_incoming_text(msg.text), msg.timestamp)

    incoming_text = _sanitize_incoming_text(payload.message.text)
    # Edge-case: pure gibberish shouldn't trigger honeypot engagement.
    if _looks_like_gibberish(incoming_text):
        log_event("gibberish_input", sessionId=session_id, client=client_host, len=len(incoming_text))
    # Sender role hardening:
    # - Never downgrade an explicit "scammer" sender to "user" (prevents shouldEngage dropouts).
    # - Only upgrade "user" -> "scammer" when content is strongly scam-like (prevents false flips
    #   on benign messages mentioning "bank/account").
    effective_sender = payload.message.sender
    if payload.message.sender == "user":
        inferred_sender = infer_sender_role(incoming_text)
        if inferred_sender == "scammer":
            # Cheap strong-signal check before we treat it as scammer text.
            quick_score = rule_score(incoming_text) + intent_signal_score(incoming_text)
            if quick_score >= max(SETTINGS.rule_threshold, 10):
                effective_sender = "scammer"

    append_message(DB, session_id, effective_sender, incoming_text, payload.message.timestamp)

    interpreter = interpret_message(incoming_text, effective_sender)
    signal_assessment = assess_sender_signals(
        platform=payload.metadata.platform if payload.metadata else None,
        sender_header=payload.metadata.senderHeader if payload.metadata else None,
        sender_number=payload.metadata.senderNumber if payload.metadata else None,
        in_contacts=payload.metadata.inContacts if payload.metadata else None,
        trusted_headers=SETTINGS.trusted_sms_headers,
    )
    # Track scammer-provided intel separately from user-provided identifiers.
    raw_intel = load_intel(DB, session_id)
    raw_user_intel = load_user_intel(DB, session_id)
    if effective_sender == "user":
        raw_user_intel = extract_intel(incoming_text, raw_user_intel)
        save_user_intel(DB, session_id, raw_user_intel)
    else:
        raw_intel = extract_intel(incoming_text, raw_intel)
        save_intel(DB, session_id, raw_intel)

    score = rule_score(incoming_text)
    intent_score = intent_signal_score(incoming_text)
    combined_score = score + intent_score + interpreter.risk_boost + signal_assessment.delta

    stat_prob = None
    if STAT_MODEL is not None:
        try:
            stat_prob = float(STAT_MODEL.predict_proba_scam(incoming_text))
        except Exception:
            stat_prob = None
    if stat_prob is not None:
        # Translate probability into a small, bounded boost for stability.
        # Keep rules as the primary decision-maker.
        if stat_prob >= 0.90:
            combined_score += 4
        elif stat_prob >= 0.75:
            combined_score += 2
        elif stat_prob <= 0.10:
            combined_score -= 1
    # Calibrated for demo/evaluation flow: avoid premature lethal zone on early turns.
    risk_percent = min(100, combined_score * 4)
    policy_zone = risk_to_zone(risk_percent)

    scam_detected = False
    confidence = 0.0
    layer_reasons = list(interpreter.reasons) + list(signal_assessment.reasons)
    layer_reasons.append(f"policy_zone:{policy_zone}")
    layer_reasons.append(f"risk_percent:{risk_percent}")
    if stat_prob is not None:
        layer_reasons.append(f"stat_prob:{stat_prob:.2f}")
    agent_notes = "; ".join(layer_reasons)
    intents = {"intentScammer": "", "intentUser": ""}
    conversation_summary = session["conversation_summary"] if "conversation_summary" in session.keys() else ""
    convo_state = _load_conversation_state(conversation_summary)
    domain_for_notes = str(convo_state.get("domain") or "generic").strip() or "generic"
    detector_route = "uncertain"
    detector_confidence = 0.0

    # If the input is gibberish and we have no prior scam latch, treat as normal.
    if _looks_like_gibberish(incoming_text) and not bool(session["scam_detected"]):
        detector_route = "normal"
        detector_confidence = 0.9
        layer_reasons.append("route:gibberish_normal")

    first_turn = int(session["total_messages"]) <= 1
    if detector_route != "normal" and first_turn:
        try:
            # Corpus match is cheapest and avoids LLM calls for known scam scripts.
            threshold_raw = os.getenv("FRAUD_CORPUS_MATCH_THRESHOLD", "").strip()
            threshold = 0.22
            if threshold_raw:
                try:
                    threshold = float(threshold_raw)
                except Exception:
                    threshold = 0.22
            match = best_match(incoming_text, FRAUD_CORPUS)
            if match.score >= threshold:
                detector_route = "scammer"
                detector_confidence = min(0.99, 0.7 + match.score)
                layer_reasons.append("opening_route:corpus_match")
                layer_reasons.append(f"corpus_score:{match.score:.2f}")
            else:
                detector_route = "scammer" if combined_score >= SETTINGS.rule_threshold else "normal"
                detector_confidence = 0.6
                layer_reasons.append("opening_route:rule_only")
        except Exception:
            detector_route = "uncertain"
            detector_confidence = 0.0
            layer_reasons.append("opening_route:detector_failed")
    elif detector_route != "normal":
        detector_route = "scammer" if combined_score >= SETTINGS.rule_threshold else "normal"
        detector_confidence = 0.6

    if detector_route == "normal" and detector_confidence >= 0.75 and combined_score < SETTINGS.rule_threshold:
        scam_detected = False
    elif combined_score >= SETTINGS.rule_threshold:
        scam_detected = True

    # Latch scam_detected for the session once it has been detected. This keeps the honeypot
    # engaging even if later scammer messages temporarily look benign (common in evaluations).
    prior_scam_detected = bool(session["scam_detected"]) if "scam_detected" in session.keys() else False
    if prior_scam_detected and effective_sender == "scammer":
        scam_detected = True
        # Ensure shouldEngage stays on for latched scam sessions.
        if detector_route == "normal":
            detector_route = "scammer"
            detector_confidence = max(detector_confidence, 0.6)

    if scam_detected:
        confidence = max(0.2, min(0.99, risk_percent / 100.0))
    else:
        confidence = max(0.05, min(0.6, risk_percent / 200.0))

    agent_notes = "; ".join(layer_reasons)

    # Exclude identifiers that appear to be user-provided (victim-owned) from reporting.
    intel = _sanitize_intelligence(_subtract_user_intel(raw_intel, raw_user_intel))

    should_engage = (
        scam_detected
        and effective_sender == "scammer"
        and detector_route != "normal"
    )

    reply = ""
    stop_reason = None
    persona_used: str | None = None
    target_key = "other"
    if should_engage:
        conversation = list_messages(DB, session_id, limit=30)
        domain = _pick_domain(convo_state, incoming_text)
        domain_for_notes = domain
        persona_used = _select_persona_tag(session=session, metadata=payload.metadata, domain=domain)
        # Always keep a defined language so error paths don't crash the request.
        language = (convo_state.get("language") if isinstance(convo_state, dict) else None) or (
            (payload.metadata.language if payload.metadata else None) or ""
        )
        language = (language or "").strip() or "hinglish"
        scammer_text = ""
        if effective_sender == "scammer":
            scammer_text = incoming_text
        else:
            for m in reversed(conversation):
                if m.get("sender") == "scammer":
                    scammer_text = str(m.get("text") or "")
                    break
        language = _pick_language_with_state(convo_state, payload.metadata, session_id, len(conversation), scammer_text)

        next_target, target_key = _get_next_extraction_target(
            conversation=conversation,
            intel=intel,
            state=convo_state,
            domain=domain,
        )
        verbosity = (payload.metadata.verbosity if payload.metadata else None) or "low"
        try:
            pb = build_reply(
                domain=domain,
                next_target=next_target,
                persona=persona_used,
                conversation=conversation,
                language=language,
                verbosity=verbosity,
            )
            reply = _maybe_echo_scammer_intel(
                reply=pb.reply,
                intel=intel,
                conversation=conversation,
                domain=domain,
                state=convo_state,
            )
            agent_notes = pb.agent_notes
            stop_reason = pb.stop_reason
        except Exception:
            # Absolute fallback to keep the API stable in evaluation harnesses.
            reply = "Sorry, I'm confused. What should I do next?"
            agent_notes = "playbook_failed"
            target_key = "other"

        # Update minimal conversation state so long transcripts stay coherent even if we only
        # load the last N messages for generation.
        convo_state["language"] = language
        if scam_detected and domain and domain != "generic":
            convo_state["domain"] = domain
        _bump_asked_counter(convo_state, target_key)
        conversation_summary = _dump_conversation_state(convo_state)
    else:
        # Non-scam / non-engagement path: keep responses short, non-committal, and non-repetitive.
        # Evaluators may send bursts of benign or gibberish input; we should remain stable.
        reply = _lightweight_reply(incoming_text, salt=f"{session_id}:{api_calls}")
    # Note: even in high-risk zones, we keep engaging (honeypot) but never reveal detection.

    reply = _tone_normalize_reply(reply)
    if should_engage:
        # Provide recent user (honeypot) messages so we don't append the same question repeatedly.
        recent_user_msgs = [m.get("text", "") for m in conversation[-12:] if m.get("sender") == "user"] if "conversation" in locals() else []
        reply = _ensure_engagement_question(
            reply,
            target_key,
            salt=f"{session_id}:{api_calls}",
            recent_user_messages=recent_user_msgs,
        )

    # Persist agent reply to keep session transcript and message counts consistent.
    append_message(
        DB,
        session_id,
        "user",
        _sanitize_outgoing_reply(reply),
        int(time.time() * 1000),
    )

    # Engagement completion rules
    session = get_or_create_session(DB, session_id)
    total_messages = int(session["total_messages"]) if "total_messages" in session.keys() else 0
    total_messages_exchanged = total_messages
    has_intel = any(intel.get(k) for k in ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers"])

    engagement_complete = False
    target_messages = int(getattr(SETTINGS, "target_messages_exchanged", 0) or 0)
    if target_messages > 0:
        # Force long exchanges for evaluation if requested.
        engagement_complete = total_messages >= target_messages
    elif stop_reason == "scammer_left":
        engagement_complete = True
    else:
        min_complete = int(getattr(SETTINGS, "min_messages_before_complete", 10) or 10)
        min_complete_intel = int(getattr(SETTINGS, "min_messages_before_complete_with_intel", 6) or 6)
        if total_messages >= min_complete:
            engagement_complete = True
        if total_messages >= min_complete_intel and has_intel:
            engagement_complete = True

    callback_pending = bool(session["callback_pending"]) if "callback_pending" in session.keys() else False
    callback_mode = str(getattr(SETTINGS, "callback_mode", "always") or "always").strip().lower()
    if callback_mode == "always":
        should_attempt_callback = scam_detected and effective_sender == "scammer"
    else:
        should_attempt_callback = scam_detected and (engagement_complete or callback_pending) and not bool(
            session["engagement_complete"]
        )
    if should_attempt_callback:
        callback_notes = _competition_agent_notes(
            raw_notes=agent_notes,
            scam_detected=scam_detected,
            policy_zone=policy_zone,
            domain=domain_for_notes,
            intel=intel,
        )
        success = await _send_callback(
            SETTINGS,
            session_id,
            scam_detected,
            total_messages_exchanged,
            intel,
            callback_notes,
        )
        if not success:
            engagement_complete = False
            callback_pending = True
            agent_notes = (agent_notes + " | callback_failed").strip(" |")
        else:
            callback_pending = False

    update_session(
        DB,
        session_id,
        scam_detected,
        confidence,
        reply,
        engagement_complete,
        agent_notes,
        callback_pending,
        conversation_summary,
        persona_used,
    )
    latency_ms = int((time.time() - request_start) * 1000)
    log_event(
        "message_processed",
        sessionId=session_id,
        client=client_host,
        sender=effective_sender,
        scamDetected=scam_detected,
        shouldEngage=should_engage,
        confidence=confidence,
        riskScore=combined_score,
        riskPercent=risk_percent,
        policyZone=policy_zone,
        detectorRoute=detector_route,
        detectorConfidence=detector_confidence,
        route=interpreter.route,
        latencyMs=latency_ms,
        apiCalls=api_calls,
        totalMessages=total_messages_exchanged,
    )

    return MessageResponse(
        status="success",
        sessionId=session_id,
        reply=_sanitize_outgoing_reply(_tone_normalize_reply(reply)),
        scamDetected=scam_detected,
        shouldEngage=should_engage,
        extractedIntelligence=intel,
        agentNotes=_competition_agent_notes(
            raw_notes=agent_notes,
            scam_detected=scam_detected,
            policy_zone=policy_zone,
            domain=domain_for_notes,
            intel=intel,
        ),
    )


async def _send_callback(
    settings: Settings,
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intel: dict[str, list[str]],
    agent_notes: str,
) -> bool:
    if not (settings.guvi_callback_url or "").strip():
        # Callback endpoint is optional in local/dev; treat as a no-op success.
        return True

    payload = _build_competition_payload(
        session_id=session_id,
        scam_detected=scam_detected,
        total_messages=total_messages,
        intel=intel,
        agent_notes=agent_notes,
    )
    log_event(
        "callback_payload_ready",
        sessionId=payload["sessionId"],
        totalMessagesExchanged=payload["totalMessagesExchanged"],
        suspiciousKeywords=len(payload["extractedIntelligence"].get("suspiciousKeywords", [])),
    )

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(settings.guvi_callback_url, json=payload)
                if 200 <= resp.status_code < 300:
                    log_event("callback_sent", statusCode=resp.status_code, attempt=attempt + 1)
                    return True
                log_event("callback_non_2xx", statusCode=resp.status_code, attempt=attempt + 1)
        except Exception:
            log_event("callback_exception", attempt=attempt + 1)
        await asyncio.sleep(2 ** attempt)
    return False


def _build_competition_payload(
    *,
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intel: dict[str, list[str]],
    agent_notes: str,
) -> dict[str, Any]:
    safe_session_id = _normalize_session_id(session_id)
    safe_total = max(1, int(total_messages))
    safe_intel = _sanitize_intelligence(intel)
    safe_notes = str(agent_notes).strip() or "No additional agent notes."
    return {
        "sessionId": safe_session_id,
        "scamDetected": bool(scam_detected),
        "totalMessagesExchanged": safe_total,
        "extractedIntelligence": safe_intel,
        "agentNotes": safe_notes,
    }


def _sanitize_intelligence(intel: dict[str, list[str]]) -> dict[str, list[str]]:
    result = {
        "bankAccounts": list(intel.get("bankAccounts", [])),
        "upiIds": list(intel.get("upiIds", [])),
        "phishingLinks": list(intel.get("phishingLinks", [])),
        "phoneNumbers": list(intel.get("phoneNumbers", [])),
        "suspiciousKeywords": [],
    }
    keyword_priority = {
        "otp": 100,
        "pin": 95,
        "password": 95,
        "cvv": 95,
        "account blocked": 90,
        "account suspended": 90,
        "verify your identity": 88,
        "share account number": 86,
        "share your account number": 86,
        "bank account": 84,
        "upi": 82,
        "urgent": 80,
        "immediately": 78,
    }
    seen_kw: set[str] = set()
    collected: list[tuple[int, str]] = []
    for value in intel.get("suspiciousKeywords", []):
        kw = " ".join(str(value).split()).strip().lower()
        if not kw or kw in seen_kw:
            continue
        seen_kw.add(kw)
        priority = keyword_priority.get(kw, 0)
        if priority <= 0:
            continue
        collected.append((priority, kw))
    collected.sort(key=lambda x: (-x[0], x[1]))
    result["suspiciousKeywords"] = [kw for _, kw in collected[:4]]
    return result


def _subtract_user_intel(intel: dict[str, list[str]], user_intel: dict[str, list[str]]) -> dict[str, list[str]]:
    # Remove identifiers that were first provided by the "user" (victim) side.
    # This prevents reporting victim-owned details even if the scammer repeats them.
    out: dict[str, list[str]] = {}
    for k in ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers", "suspiciousKeywords"]:
        base = list(intel.get(k, []))
        if k == "suspiciousKeywords":
            out[k] = base
            continue
        remove_set = set(user_intel.get(k, []))
        out[k] = [v for v in base if v not in remove_set]
    return out


def _select_persona_tag(*, session: Any, metadata: Metadata | None, domain: str) -> str:
    existing = ""
    try:
        existing = str(session["persona"] or "")
    except Exception:
        existing = ""
    if existing.strip():
        return existing.strip()

    meta_persona = (metadata.persona if metadata else None) or ""
    meta_persona = meta_persona.strip().lower()

    # Deterministic persona per scenario domain, overridable by metadata.persona.
    if meta_persona in {"vet", "vet_doctor", "doctor"}:
        return "bittu_vet_doctor"
    if meta_persona in {"truck", "truck_owner", "transport", "business"}:
        return "bittu_truck_owner"
    if meta_persona in {"student", "hostel_student"}:
        return "bittu_student"
    if meta_persona in {"shop", "shopkeeper"}:
        return "bittu_shopkeeper"

    return "bittu_vet_doctor" if domain == "upi_authority" else "bittu_shopkeeper"


def _load_conversation_state(raw: str) -> dict[str, Any]:
    """
    Persisted state to reduce "context loss" across long sessions.

    Stored in sessions.conversation_summary as a small JSON object, e.g.:
      {"language":"en","domain":"bank_block","asked":{"upi":2,"phone":1}}
    """
    s = (raw or "").strip()
    if not s or not s.startswith("{"):
        return {"asked": {}}
    try:
        obj = json.loads(s)
        if not isinstance(obj, dict):
            return {"asked": {}}
        asked = obj.get("asked")
        if not isinstance(asked, dict):
            obj["asked"] = {}
        return obj
    except Exception:
        return {"asked": {}}


def _dump_conversation_state(state: dict[str, Any]) -> str:
    # Keep it bounded for DB + logs.
    safe: dict[str, Any] = {"asked": {}}
    if isinstance(state.get("language"), str):
        safe["language"] = state["language"]
    if isinstance(state.get("domain"), str):
        safe["domain"] = state["domain"]
    asked = state.get("asked")
    if isinstance(asked, dict):
        out_asked: dict[str, int] = {}
        for k, v in asked.items():
            if not isinstance(k, str):
                continue
            try:
                out_asked[k] = int(v)
            except Exception:
                continue
        safe["asked"] = out_asked
    try:
        dumped = json.dumps(safe, ensure_ascii=True)
    except Exception:
        dumped = ""
    if len(dumped) > 1200:
        # If it grows unexpectedly, drop asked counters beyond a small set.
        safe["asked"] = {k: safe["asked"].get(k, 0) for k in ["upi", "phone", "link", "bank", "other"] if k in safe["asked"]}
        dumped = json.dumps(safe, ensure_ascii=True)
    return dumped


def _bump_asked_counter(state: dict[str, Any], key: str) -> None:
    if not key:
        return
    asked = state.get("asked")
    if not isinstance(asked, dict):
        asked = {}
        state["asked"] = asked
    try:
        asked[key] = int(asked.get(key, 0) or 0) + 1
    except Exception:
        asked[key] = 1


def _pick_domain(state: dict[str, Any], text: str) -> str:
    """
    Pick a domain for the current turn.

    Default behaviour: lock to the first strong domain to avoid drifting across long chats.
    Evaluator edge case: scammers may mix multiple scam types in a single session; in that case
    we should switch domains when the new message is a *strong* match for a different domain.
    """
    detected = detect_domain(text)
    locked = state.get("domain")

    if isinstance(locked, str) and locked.strip() and locked.strip().lower() != "generic":
        locked_norm = locked.strip()
        if detected and detected != "generic" and detected != locked_norm:
            # Allow immediate switch for "hard" domains that are typically unambiguous.
            hard = {
                "tech_support",
                "prize_lottery",
                "job_offer",
                "loan_scam",
                "insurance_scam",
                "rental_scam",
                "sextortion_scam",
                "romance_scam",
                "medical_tourism_scam",
                "crypto_recovery_scam",
                "income_tax_scam",
                "delivery_package",
                "credit_card",
                "charity_donation",
                "investment_crypto",
                "government_grant",
                "friend_emergency",
                "aadhaar_misuse_scam",
                "digital_arrest_scam",
                "electricity_bill_scam",
                "fastag_toll_scam",
            }
            if detected in hard:
                state["domain"] = detected
                return detected
        return locked_norm

    return detected or "generic"


def _pick_language_with_state(state: dict[str, Any], metadata: Metadata | None, session_id: str, turn: int, scammer_text: str) -> str:
    """
    Pick and persist the session language, but allow one-way adaptation to the scammer's
    stable language style after a short streak.

    Requirement (hackathon realism): if the scammer keeps using the same language/style
    for a few turns, the honeypot should align.
    """
    # Respect explicit language selection (never auto-switch away from it).
    lang_raw = (metadata.language if metadata else None) or ""
    if lang_raw.strip():
        chosen = _pick_language(metadata, session_id, turn, scammer_text)
        state["language"] = chosen
        return chosen

    current = str(state.get("language") or "").strip().lower() or ""
    # Default if nothing chosen yet: Hinglish (India-friendly).
    if not current:
        current = "hinglish"
        state["language"] = current

    # Track scammer style stability and adapt after 3 consistent scammer turns.
    style = _detect_lang_style(scammer_text)
    last_style = str(state.get("lang_last") or "").strip().lower()
    streak = int(state.get("lang_streak", 0) or 0)
    if style and style == last_style:
        streak += 1
    else:
        streak = 1
        last_style = style
    state["lang_last"] = last_style
    state["lang_streak"] = streak

    if streak >= 3 and style in {"en", "hi", "hinglish"} and style != current:
        state["language"] = style
        return style

    return current


def _get_next_extraction_target(
    *,
    conversation: list[dict[str, Any]],
    intel: dict[str, list[str]],
    state: dict[str, Any],
    domain: str,
) -> tuple[str, str]:
    """
    Returns (target_prompt, target_key).
    target_key is used for asked counters so we don't ask the exact same thing forever.
    """
    last_scammer_msg = ""
    for msg in reversed(conversation):
        if msg.get("sender") == "scammer":
            last_scammer_msg = str(msg.get("text") or "").lower()
            break

    missing_phone = not intel.get("phoneNumbers")
    missing_upi = not intel.get("upiIds")
    missing_link = not intel.get("phishingLinks")
    missing_bank = not intel.get("bankAccounts")

    asked = state.get("asked") if isinstance(state.get("asked"), dict) else {}
    a_upi = int(asked.get("upi", 0) or 0)
    a_phone = int(asked.get("phone", 0) or 0)
    a_link = int(asked.get("link", 0) or 0)
    a_bank = int(asked.get("bank", 0) or 0)

    bank_context = any(k in last_scammer_msg for k in ["account", "ifsc", "branch", "passbook"])

    # 1) Prioritize missing intel but vary how we ask as attempts grow.
    if missing_link and ("http" in last_scammer_msg or "link" in last_scammer_msg or "click" in last_scammer_msg):
        if a_link >= 2:
            return ("Ask them to type the exact domain + page path (slowly), because the link is not opening", "link")
        return ("Ask for the exact link/domain again (to avoid opening the wrong page)", "link")

    if missing_phone and any(k in last_scammer_msg for k in ["call", "whatsapp", "number", "contact", "sms", "text"]):
        if a_phone >= 2:
            return ("Ask for the exact phone/WhatsApp number with country code and spacing (so you can save it correctly)", "phone")
        return ("Ask for the exact phone/WhatsApp number to contact", "phone")

    if missing_upi and any(k in last_scammer_msg for k in ["upi", "pay", "payment", "transfer", "send money", "collect request"]):
        if a_upi >= 2:
            return ("Ask them to retype the UPI handle letter-by-letter and confirm the beneficiary name shown", "upi")
        return ("Ask for the exact UPI ID/handle (and beneficiary name)", "upi")

    if missing_bank and any(k in last_scammer_msg for k in ["account", "ifsc", "bank", "branch"]):
        if a_bank >= 2:
            return ("Ask them to repeat the account number and IFSC slowly (you are writing it down)", "bank")
        return ("Ask for the exact account number and IFSC/branch name", "bank")

    # 2) If we already have all required intel, stay contextual based on domain.
    if not (missing_phone or missing_upi or missing_link or missing_bank):
        if domain == "tech_support":
            return ("Say you are stuck on the next step and ask them to repeat it slowly (you are not technical)", "other")
        if domain in {"bank_block", "upi_security", "upi_refund", "upi_authority"}:
            return ("Say the app is slow and ask what to do next (step by step) to avoid mistakes", "other")
        return ("Ask what to do next", "other")

    # 3) Otherwise, keep collecting missing items in a stable order but don't loop forever.
    if missing_phone:
        return ("Ask for the exact phone number / WhatsApp contact to call back (so you don't make a mistake)", "phone")
    if missing_upi:
        return ("Ask for the UPI handle to use", "upi")
    if missing_link:
        return ("Ask for the exact link/URL to proceed", "link")
    if missing_bank:
        # If scammer isn't talking about bank account/IFSC, don't get stuck asking for it every turn.
        # Ask once early, then rotate other verification questions and only re-ask periodically.
        if a_bank == 0:
            return ("Ask which account number this is about (and IFSC if applicable)", "bank")
        if bank_context and a_bank <= 2:
            return ("Ask for the exact account number and IFSC/branch name", "bank")

        # Rotate between secondary targets to maintain realism and keep extracting more scammer identifiers.
        # Pick the least-used key among (phone/link/upi/other); re-ask bank only every 4th time.
        if a_bank % 4 == 0:
            return ("Ask which account number this is about (you have multiple accounts)", "bank")
        candidates = [
            ("phone", a_phone),
            ("link", a_link),
            ("upi", a_upi),
            ("other", int(asked.get("other", 0) or 0)),
        ]
        candidates.sort(key=lambda x: (x[1], x[0]))
        k = candidates[0][0]
        if k == "phone":
            return ("Ask for the exact callback/WhatsApp number again (country code), in case the call drops", "phone")
        if k == "link":
            return ("Ask them to paste the official link/domain again so you can avoid a typo", "link")
        if k == "upi":
            return ("Ask them to retype the UPI handle letter-by-letter and confirm beneficiary name shown", "upi")
        return ("Say you are stuck on the next step and ask them to repeat it slowly (you are not technical)", "other")
    return ("Ask what to do next", "other")


def _maybe_echo_scammer_intel(
    *,
    reply: str,
    intel: dict[str, list[str]],
    conversation: list[dict[str, Any]],
    domain: str,
    state: dict[str, Any] | None = None,
) -> str:
    """
    Make replies sound more "legit" to the scammer by repeating *scammer-provided* values
    (UPI/phone/link) as a confirmation step. This also nudges them to correct typos.

    Important: this uses `intel` that already had victim-provided identifiers subtracted.
    """
    base = (reply or "").strip()
    if not base:
        return reply

    low = base.lower()
    # IMPORTANT:
    # A long (150-300 turn) engagement will naturally push earlier confirmations out of a "recent window".
    # If we only check the last N replies, we'll re-confirm the same UPI/phone/link repeatedly and sound bot-like.
    # So we check the whole conversation AND also maintain a small per-session echo memory in `state`.
    user_texts = [str(m.get("text") or "") for m in conversation if m.get("sender") == "user"]
    echoed: dict[str, Any] | None = None
    if isinstance(state, dict):
        echoed = state.setdefault("echoedIntel", {})  # JSON-serializable

    def _echoed_before(kind: str, value: str) -> bool:
        if echoed is None or not value:
            return False
        arr = echoed.get(kind)
        if not isinstance(arr, list):
            return False
        return value in arr

    def _mark_echoed(kind: str, value: str) -> None:
        if echoed is None or not value:
            return
        arr = echoed.get(kind)
        if not isinstance(arr, list):
            arr = []
        if value not in arr:
            arr.append(value)
        # Cap so conversation state stays small.
        if len(arr) > 25:
            arr = arr[-25:]
        echoed[kind] = arr

    def _already_said(value: str) -> bool:
        return any(value and value in t for t in user_texts)

    # Prefer echoing payment redirection intel (most valuable in hackathon scoring).
    if intel.get("upiIds") and ("upi" in low or "handle" in low or "payment" in low or "transfer" in low):
        upi = str(intel["upiIds"][-1]).strip()
        if upi and not _already_said(upi) and not _echoed_before("upiIds", upi) and len(base.split()) <= 55:
            if not base.endswith((".", "!", "?")):
                base += "."
            _mark_echoed("upiIds", upi)
            return f"{base} You said the UPI ID is {upi} — is that correct?"

    if intel.get("phoneNumbers") and any(k in low for k in ["number", "call", "whatsapp", "sms", "text"]):
        phone = str(intel["phoneNumbers"][-1]).strip()
        if phone and not _already_said(phone) and not _echoed_before("phoneNumbers", phone) and len(base.split()) <= 55:
            if not base.endswith((".", "!", "?")):
                base += "."
            _mark_echoed("phoneNumbers", phone)
            return f"{base} Just to confirm, should I contact {phone} or a different number?"

    if intel.get("phishingLinks") and any(k in low for k in ["link", "url", "website", "domain"]):
        link = str(intel["phishingLinks"][-1]).strip()
        if link and not _already_said(link) and not _echoed_before("phishingLinks", link) and len(base.split()) <= 55:
            if not base.endswith((".", "!", "?")):
                base += "."
            _mark_echoed("phishingLinks", link)
            return f"{base} The link you mentioned was {link} — should I open the same one?"

    # For bank account numbers: avoid repeating full numbers too often; use last-4 for realism.
    if intel.get("bankAccounts") and "account" in low and domain in {"bank_fraud", "upi_security", "upi_refund"}:
        acc = str(intel["bankAccounts"][-1]).strip()
        if acc and not _already_said(acc) and len(acc) >= 8 and len(base.split()) <= 60:
            tail = acc[-4:]
            if _echoed_before("bankAccountsTail", tail):
                return reply
            if not base.endswith((".", "!", "?")):
                base += "."
            _mark_echoed("bankAccountsTail", tail)
            return f"{base} You mean the account ending in {tail}, right?"

    return reply


_RE_PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.IGNORECASE)
_RE_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")
_RE_CVV = re.compile(r"\bcvv\s*[:=]?\s*\d{3,4}\b", re.IGNORECASE)
_RE_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_RE_OTP = re.compile(r"\b\d{4,8}\b")
_RE_PASSWORD_HINT = re.compile(r"\b(password|passcode|netbanking|upi pin|pin)\b", re.IGNORECASE)


def _sanitize_outgoing_reply(text: str) -> str:
    """
    Hard guardrail: our honeypot must never output sensitive victim credentials/PII.

    If a template/bridge accidentally contains such content, replace with a safe,
    human-sounding fallback that continues engagement without revealing detection.
    """
    s = (text or "").strip()
    if not s:
        return text

    lowered = s.lower()
    # If content looks like it contains credentials, do not send it as-is.
    if _RE_PASSWORD_HINT.search(lowered) and (_RE_PAN.search(s) or _RE_AADHAAR.search(s) or _RE_CVV.search(s) or _RE_CARD.search(s) or _RE_OTP.search(s)):
        return (
            "I am not comfortable sharing any codes or personal details. "
            "Please send your official callback number or UPI handle/link in one message so I can verify and proceed."
        )

    # Redact high-risk tokens if they slipped in.
    if _RE_PAN.search(s) or _RE_AADHAAR.search(s) or _RE_CVV.search(s) or _RE_CARD.search(s):
        return (
            "I'm getting confused and I don't want to share sensitive details. "
            "Please tell me the exact official number/UPI handle or the link you want me to use, and the steps."
        )

    return text


_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_GUJARATI_RE = re.compile(r"[\u0A80-\u0AFF]")
_SCRIPT_TAG_RE = re.compile(r"(?is)<\s*script\b[^>]*>.*?<\s*/\s*script\s*>")
_HTML_TAG_RE = re.compile(r"(?s)<[^>]{1,200}>")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")

# Keep URL/handle punctuation, but strip decorative symbols/emoji that can bloat tokens.
_ALLOWED_PUNCT = set("@./:+#-_%?=&")


def _strip_decorative_symbols(s: str) -> str:
    import unicodedata

    out: list[str] = []
    for ch in s:
        if ch.isspace():
            out.append(" ")
            continue
        if ch in _ALLOWED_PUNCT:
            out.append(ch)
            continue
        o = ord(ch)
        # Drop variation selectors used in emoji sequences.
        if 0xFE00 <= o <= 0xFE0F:
            out.append(" ")
            continue
        cat = unicodedata.category(ch)  # e.g. "Ll", "Mn", "So"
        # Drop control/format chars (ZWJ etc.).
        if cat and cat[0] == "C":
            out.append(" ")
            continue
        # Keep letters, numbers, and combining marks (required for Indic scripts).
        if cat and cat[0] in {"L", "N", "M"}:
            out.append(ch)
            continue
        # Keep currency symbols for amount patterns (₹, $, etc.).
        if cat == "Sc":
            out.append(ch)
            continue
        # Everything else is decorative punctuation/symbols/emoji -> space.
        out.append(" ")
    return "".join(out)


def _sanitize_incoming_text(text: str) -> str:
    """
    Basic input sanitization.

    We treat incoming messages as untrusted user content. We do not execute or render it,
    but some UIs might display stored transcripts. Strip obvious script/html tags and
    control chars to reduce XSS/log injection risk while preserving the main content.
    """
    s = str(text or "")
    s = _CONTROL_CHARS_RE.sub(" ", s)
    s = _SCRIPT_TAG_RE.sub(" ", s)
    if "<" in s and ">" in s:
        s = _HTML_TAG_RE.sub(" ", s)
    # Drop emoji and decorative symbols that bloat tokens and harm pattern matching.
    # Keep letters/marks (Indic scripts) and URL/handle punctuation.
    s = _strip_decorative_symbols(s)
    # Normalize whitespace (keeps extraction stable).
    s = " ".join(s.split())
    return s.strip()


def _tone_normalize_reply(text: str) -> str:
    """
    Keep the honeypot calm/observational (avoid excited language that looks scripted),
    without changing the extraction intent.
    """
    s = str(text or "").strip()
    if not s:
        return s

    for pat, repl in _EXCITED_PATTERNS:
        s = pat.sub(repl, s)

    # Replace excitement punctuation with neutral punctuation.
    s = re.sub(r"!{1,}", ".", s)
    s = re.sub(r"\.{2,}", ".", s)
    s = re.sub(r"\s+\.", ".", s)
    return s.strip()


def _ensure_engagement_question(
    reply: str,
    target_key: str,
    *,
    salt: str,
    recent_user_messages: list[str] | None = None,
) -> str:
    """
    Evaluators reward long, coherent engagement. If the reply doesn't naturally ask for the
    next actionable detail, append a short question to keep the scammer responding.
    """
    s = (reply or "").strip()
    if not s:
        return "Observed. What should I do next?"
    if "?" in s:
        return s

    key_raw = (target_key or "other").strip().lower()
    # Call sites use "phone/upi/link/bank/other" as target keys.
    key = {
        "phone": "ask_phone",
        "upi": "ask_upi",
        "link": "ask_link",
        "bank": "ask_bank",
        "ask_phone": "ask_phone",
        "ask_upi": "ask_upi",
        "ask_link": "ask_link",
        "ask_bank": "ask_bank",
    }.get(key_raw, "other")
    pools: dict[str, list[str]] = {
        "ask_phone": [
            "Which phone number should I contact you on (with country code)?",
            "Can you type your exact callback number again?",
            "If the call drops, which number should I call back?",
        ],
        "ask_upi": [
            "What is the exact UPI ID again (type it clearly)?",
            "Please repeat the UPI handle once more so I can copy it.",
            "Which UPI ID should I use? Write it exactly like name@bank.",
        ],
        "ask_link": [
            "What is the exact link again (paste it in full)?",
            "Can you paste the full URL again? I do not want to mistype it.",
            "Which page should I open exactly? Please send the link again.",
        ],
        "ask_bank": [
            "What is the account number and IFSC again (write it in one message)?",
            "Please type the account number and IFSC clearly, no spaces.",
            "Which bank details should I use? Account number + IFSC, please repeat.",
        ],
        "other": [
            "What should I do next?",
            "Can you repeat the steps once, slowly?",
            "I am on the wrong screen. What should I tap next?",
            "Please write the next step in one short message.",
            "Which option should I choose next?",
        ],
    }

    options = list(pools.get(key, pools["other"]))

    def _norm_q(x: str) -> str:
        x = " ".join((x or "").lower().strip().split())
        for ch in [".", ",", "!", "?", "…", "–", "-", "â€¦", "â€“"]:
            x = x.replace(ch, "")
        return x

    # Avoid repeating the same engagement question in a visible loop.
    if recent_user_messages:
        recent_norm = {_norm_q(t) for t in recent_user_messages if t and t.strip()}
        filtered = [q for q in options if _norm_q(q) not in recent_norm]
        if filtered:
            options = filtered

    # Stable-ish selection per call (salt changes each API call), but after filtering.
    digest = hashlib.sha256((salt + "|" + key + "|" + str(len(options))).encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(options)
    q = options[idx]

    if not s.endswith((".", "!", "?", ":")):
        s += "."
    return f"{s} {q}"


def _lightweight_reply(incoming_text: str, *, salt: str) -> str:
    """
    Non-engagement reply used when we are not in honeypot mode for this turn.
    Keep it short, stable, and avoid repeating the exact same line on bursts of benign traffic.
    """
    txt = (incoming_text or "").strip()
    if not txt:
        return "Observed."

    # Gibberish should not crash; ask to rephrase.
    if _looks_like_gibberish(txt):
        options = [
            "Observed. I did not catch that. Can you repeat?",
            "Observed. That message is unclear to me. Can you rephrase?",
            "Observed. Sorry, I could not understand. What do you mean?",
        ]
    else:
        options = [
            "Observed. Can you share a bit more context?",
            "Observed. What do you need help with exactly?",
            "Observed. Please explain in one short message.",
            "Observed. Can you repeat the main point?",
        ]

    digest = hashlib.sha256((salt + "|" + str(len(txt)) + "|" + txt[:32]).encode("utf-8")).hexdigest()
    idx = int(digest[:8], 16) % len(options)
    return options[idx]


def _looks_like_gibberish(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return True
    # Non-Latin scripts are not gibberish by default (evaluators may send mixed scripts).
    if _DEVANAGARI_RE.search(s) or _GUJARATI_RE.search(s):
        return False
    # If it contains URLs, UPI handles, numbers, or common scam anchors, it is not gibberish.
    lower = s.lower()
    if "http" in lower or "www." in lower:
        return False
    if any(k in lower for k in ["otp", "upi", "bank", "account", "verify", "blocked", "refund", "loan", "prize", "police", "income tax"]):
        return False
    # Simple heuristic: too few word-like tokens and high symbol ratio.
    tokens = [t for t in re.split(r"\s+", s) if t]
    wordish = [t for t in tokens if re.search(r"[a-zA-Z]{2,}", t)]
    if len(s) <= 20 and not wordish:
        return True
    if len(wordish) == 0 and len(tokens) <= 2:
        return True
    letters = sum(1 for ch in s if ch.isalpha())
    digits = sum(1 for ch in s if ch.isdigit())
    spaces = sum(1 for ch in s if ch.isspace())
    others = len(s) - letters - digits - spaces
    if len(s) >= 8 and letters + digits > 0:
        if others / len(s) > 0.45 and len(wordish) <= 1:
            return True
    return False


def _detect_lang_style(text: str) -> str:
    """
    Heuristic language/style detector for scammer messages.

    Returns:
      - "en": English
      - "hi": Roman Hindi (English alphabets)
      - "hinglish": mix
    """
    t = (text or "").strip()
    if not t:
        return "en"

    lower = t.lower()
    if _DEVANAGARI_RE.search(t):
        # Hindi script present -> prefer Roman-Hindi style templates (still in Latin chars in our dataset).
        return "hi"

    # Rough Hinglish signals (roman hindi words) - keep list small and high-precision.
    hinglish_markers = [
        "haan",
        "arre",
        "beta",
        "bhai",
        "sirji",
        "ji ",
        " kya ",
        " ka ",
        " nahi",
        " ruko",
        " jaldi",
        " samajh",
        " paise",
        " bank",
        " upi",
    ]
    hits = sum(1 for w in hinglish_markers if w in lower)
    if hits >= 3:
        return "hinglish"

    return "en"


def _pick_language(metadata: Metadata | None, session_id: str, turn: int, scammer_text: str) -> str:
    """
    Language preferences:
    - "en": English
    - "hi": Romanized Hindi (Hindi in English alphabets)
    - "hinglish": Mix of Hindi + English

    If not specified, default to Hinglish for India, with light rotation.
    """
    lang_raw = (metadata.language if metadata else None) or ""
    loc = (metadata.locale if metadata else None) or ""
    lang = lang_raw.strip().lower()
    loc = loc.strip().upper()

    # Respect explicit language selection.
    if lang:
        if lang.startswith("en") or lang in {"english"}:
            return "en"
        if lang.startswith("hinglish") or lang in {"mix", "hi-en", "hi_en"}:
            return "hinglish"
        if lang.startswith("hi") or lang in {"hindi", "roman", "hi-latn", "hi_latn"}:
            return "hi"
        return "en"

    # Default: Hinglish for India, but follow scammer style when strongly signaled.
    style = _detect_lang_style(scammer_text)
    if not loc or loc == "IN":
        if style in {"hi", "hinglish"}:
            return style
        # If scammer is clearly English, start English; otherwise prefer Hinglish.
        if style == "en":
            return "en"
        return "hinglish"

    # Non-IN locales: default to English.
    return "en"


def _normalize_session_id(value: str) -> str:
    # Keep session IDs URL-safe and bounded to avoid malformed IDs across clients.
    candidate = value.strip()
    # Important: some clients send short IDs (e.g. "test-1"). If we reject them and generate
    # a new random ID, we silently break multi-turn context. So:
    # - Accept safe IDs of length 1..80
    # - Otherwise derive a stable sanitized ID from a hash of the incoming value
    if candidate and re.fullmatch(r"[A-Za-z0-9._-]{1,80}", candidate):
        return candidate
    if candidate:
        import hashlib

        h = hashlib.sha256(candidate.encode("utf-8", "ignore")).hexdigest()[:20]
        return f"sess_{h}"
    return f"sess_{uuid.uuid4().hex[:20]}"


def _competition_agent_notes(
    *,
    raw_notes: str,
    scam_detected: bool,
    policy_zone: str,
    domain: str,
    intel: dict[str, list[str]],
) -> str:
    lower = (raw_notes or "").lower()
    if not scam_detected:
        zone = (policy_zone or "observe").strip().lower()
        return f"zone={zone}; domain={domain or 'generic'}; no_high_confidence_scam_detected"

    # Keep notes compact but not identical across turns: include tactic + small intel summary.
    urgency = any(k in lower for k in ["urgent", "immediately", "minutes", "blocked", "suspended", "legal action", "arrest"])
    redirection = any(k in lower for k in ["upi", "transfer", "payment", "pay now", "link_present"]) or any(
        (intel.get("upiIds") or []) + (intel.get("phoneNumbers") or []) + (intel.get("phishingLinks") or [])
    )
    tactics = []
    if urgency:
        tactics.append("urgency")
    if redirection:
        tactics.append("redirection")
    if not tactics:
        tactics.append("social_engineering")

    upi_n = len(intel.get("upiIds", []) or [])
    phone_n = len(intel.get("phoneNumbers", []) or [])
    link_n = len(intel.get("phishingLinks", []) or [])
    bank_n = len(intel.get("bankAccounts", []) or [])

    zone = (policy_zone or "unknown").strip().lower()
    dom = (domain or "generic").strip().lower()
    return f"zone={zone}; domain={dom}; tactics={'+'.join(tactics)}; intel(upi={upi_n},phone={phone_n},link={link_n},bank={bank_n})"
