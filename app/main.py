import asyncio
import os
import re
import time
import uuid
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

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
    save_intel,
    update_session,
)
from .intel import extract_intel, infer_sender_role, intent_signal_score, rule_score
from .hardening import (
    CircuitBreaker,
    SlidingWindowLimiter,
    log_event,
    setup_logging,
    validate_agent_result,
    validate_llm_result,
)
from .layers import interpret_message, merge_intelligence, normalize_intelligence
from .llm import GroqClient, pick_persona
from .signal_policy import assess_sender_signals, risk_to_zone
from .fraud_corpus import best_match, load_corpus_lines

app = FastAPI(title="Agentic Honeypot API")

SETTINGS: Settings | None = None
DB = None
GROQ: GroqClient | None = None
FRAUD_CORPUS: list[str] = []
LLM_CIRCUIT = CircuitBreaker(failure_threshold=4, recovery_seconds=45)
REQ_LIMITER = SlidingWindowLimiter(max_requests=80, window_seconds=60)


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
    global SETTINGS, DB, GROQ, FRAUD_CORPUS
    setup_logging()
    SETTINGS = load_settings()
    DB = connect(SETTINGS.db_path)
    init_db(DB)
    FRAUD_CORPUS = load_corpus_lines()
    GROQ = GroqClient(
        base_url=SETTINGS.groq_base_url,
        api_keys=SETTINGS.groq_api_keys,
        model=SETTINGS.groq_model,
        local_enabled=SETTINGS.local_llm_enabled,
        ollama_base_url=SETTINGS.ollama_base_url,
        ollama_model=SETTINGS.ollama_model,
    )
    log_event(
        "startup_complete",
        model=SETTINGS.groq_model,
        db_path=SETTINGS.db_path,
        firebaseEnabled=SETTINGS.firebase_enabled,
        firebaseProjectId=SETTINGS.firebase_project_id,
        fraudCorpusLines=len(FRAUD_CORPUS),
        localLlmEnabled=SETTINGS.local_llm_enabled,
        ollamaModel=SETTINGS.ollama_model,
    )


@app.post("/api/message", response_model=MessageResponse)
@app.post("/analyze", response_model=MessageResponse)
async def handle_message(
    payload: MessageRequest,
    request: Request,
    _auth: None = Depends(require_api_key),
) -> MessageResponse:
    if SETTINGS is None or DB is None or GROQ is None:
        raise HTTPException(status_code=500, detail="Service not initialized")
    request_start = time.time()
    incoming_session_id = (payload.sessionId or "").strip()
    session_id = _normalize_session_id(incoming_session_id)
    if session_id != incoming_session_id:
        log_event("session_id_normalized", incomingSessionId=incoming_session_id, sessionId=session_id)

    client_host = request.client.host if request.client else "unknown"
    limiter_key = f"{client_host}:{session_id}"
    if not REQ_LIMITER.allow(limiter_key):
        log_event("rate_limited", sessionId=session_id, client=client_host)
        raise HTTPException(status_code=429, detail="Too many requests")

    session = get_or_create_session(DB, session_id)
    increment_api_calls(DB, session_id)
    api_calls = get_api_calls(DB, session_id)
    if int(session["total_messages"]) == 0 and payload.conversationHistory:
        for msg in payload.conversationHistory:
            append_message(DB, session_id, msg.sender, msg.text, msg.timestamp)

    inferred_sender = infer_sender_role(payload.message.text)
    effective_sender = payload.message.sender
    if inferred_sender != payload.message.sender:
        effective_sender = inferred_sender

    append_message(DB, session_id, effective_sender, payload.message.text, payload.message.timestamp)

    interpreter = interpret_message(payload.message.text, effective_sender)
    signal_assessment = assess_sender_signals(
        platform=payload.metadata.platform if payload.metadata else None,
        sender_header=payload.metadata.senderHeader if payload.metadata else None,
        sender_number=payload.metadata.senderNumber if payload.metadata else None,
        in_contacts=payload.metadata.inContacts if payload.metadata else None,
        trusted_headers=SETTINGS.trusted_sms_headers,
    )
    intel = load_intel(DB, session_id)
    intel = extract_intel(payload.message.text, intel)

    score = rule_score(payload.message.text)
    intent_score = intent_signal_score(payload.message.text)
    combined_score = score + intent_score + interpreter.risk_boost + signal_assessment.delta
    # Calibrated for demo/evaluation flow: avoid premature lethal zone on early turns.
    risk_percent = min(100, combined_score * 4)
    policy_zone = risk_to_zone(risk_percent)

    scam_detected = False
    confidence = 0.0
    layer_reasons = list(interpreter.reasons) + list(signal_assessment.reasons)
    layer_reasons.append(f"policy_zone:{policy_zone}")
    layer_reasons.append(f"risk_percent:{risk_percent}")
    agent_notes = "; ".join(layer_reasons)
    intents = {"intentScammer": "", "intentUser": ""}
    conversation_summary = session["conversation_summary"] if "conversation_summary" in session.keys() else ""
    detector_route = "uncertain"
    detector_confidence = 0.0

    first_turn = int(session["total_messages"]) <= 1
    if first_turn:
        try:
            # Corpus match is cheapest and avoids LLM calls for known scam scripts.
            threshold_raw = os.getenv("FRAUD_CORPUS_MATCH_THRESHOLD", "").strip()
            threshold = 0.22
            if threshold_raw:
                try:
                    threshold = float(threshold_raw)
                except Exception:
                    threshold = 0.22
            match = best_match(payload.message.text, FRAUD_CORPUS)
            if match.score >= threshold:
                detector_route = "scammer"
                detector_confidence = min(0.99, 0.7 + match.score)
                layer_reasons.append("opening_route:corpus_match")
                layer_reasons.append(f"corpus_score:{match.score:.2f}")
            else:
                if LLM_CIRCUIT.allow_request():
                    detector = await GROQ.detect_opening_route(payload.message.text)
                    detector_route = str(detector.get("route", "uncertain"))
                    detector_confidence = float(detector.get("confidence", 0.0))
                    layer_reasons.append(f"opening_route:{detector_route}")
                else:
                    detector_route = "scammer" if combined_score >= SETTINGS.rule_threshold else "normal"
                    detector_confidence = 0.6
                    layer_reasons.append("opening_route:rule_fallback")
        except Exception:
            detector_route = "uncertain"
            detector_confidence = 0.0
            layer_reasons.append("opening_route:detector_failed")

    used_rule_fallback = False
    try:
        if detector_route == "normal" and detector_confidence >= 0.75 and combined_score < SETTINGS.rule_threshold:
            llm_result = {
                "scamDetected": False,
                "confidence": detector_confidence,
                "reasons": ["opening_normal_short_circuit"],
            }
        else:
            recent_messages = list_messages(DB, session_id, limit=40)
            context = "\n".join([f"{m['sender']}: {m['text']}" for m in recent_messages])
            if LLM_CIRCUIT.allow_request():
                intents = await GROQ.summarize_intents(recent_messages)
                if hasattr(GROQ, "extract_structured_intel"):
                    raw_intel = await GROQ.extract_structured_intel(payload.message.text, context=context)
                    intel = merge_intelligence(intel, normalize_intelligence(raw_intel))
            else:
                layer_reasons.append("circuit_open")
                used_rule_fallback = True
            if int(session["total_messages"]) % 6 == 0:
                if LLM_CIRCUIT.allow_request():
                    conversation_summary = await GROQ.summarize_conversation(
                        recent_messages[-12:],
                        conversation_summary,
                    )
            context = f"Summary: {conversation_summary}\n\n{context}" if conversation_summary else context
            if combined_score >= SETTINGS.rule_threshold + 6:
                llm_result = {"scamDetected": True, "confidence": 0.99, "reasons": ["strong_rule_match"]}
            elif interpreter.route == "lightweight" and combined_score < SETTINGS.rule_threshold:
                llm_result = {"scamDetected": False, "confidence": 0.2, "reasons": ["lightweight_route"]}
            elif not LLM_CIRCUIT.allow_request():
                llm_result = {"scamDetected": combined_score >= SETTINGS.rule_threshold, "confidence": 0.25, "reasons": ["rule_only_mode"]}
                used_rule_fallback = True
            else:
                llm_result = await GROQ.classify(payload.message.text, context=context, intents=intents)
        llm_result = validate_llm_result(llm_result)
        scam_detected = bool(llm_result["scamDetected"])
        confidence = float(llm_result["confidence"])
        layer_reasons.extend(llm_result.get("reasons", []))
        agent_notes = "; ".join(layer_reasons)
        LLM_CIRCUIT.record_success()
    except Exception:
        llm_result = {"scamDetected": False, "confidence": 0.0, "reasons": []}
        LLM_CIRCUIT.record_failure()
        used_rule_fallback = True
        if not agent_notes:
            agent_notes = "llm_layer_failed"

    intel = _sanitize_intelligence(intel)
    save_intel(DB, session_id, intel)

    if detector_route == "normal" and detector_confidence >= 0.75 and combined_score < SETTINGS.rule_threshold:
        scam_detected = False
    elif combined_score >= SETTINGS.rule_threshold or confidence >= SETTINGS.llm_threshold:
        scam_detected = True

    should_engage = (
        scam_detected
        and effective_sender == "scammer"
        and policy_zone != "lethal"
        and detector_route != "normal"
    )

    reply = "Thanks. Can you share more details?"
    stop_reason = None
    persona_used: str | None = None
    if should_engage:
        conversation = list_messages(DB, session_id, limit=30)
        persona_used = pick_persona()
        try:
            if LLM_CIRCUIT.allow_request():
                agent = await GROQ.generate_reply(
                    persona_used,
                    conversation,
                    intel,
                    intents=intents,
                    suspected_scammer=True,
                )
                safe_agent = validate_agent_result(agent, reply, agent_notes)
                reply = safe_agent["reply"]
                agent_notes = safe_agent["agentNotes"]
                stop_reason = safe_agent["stopReason"]
                LLM_CIRCUIT.record_success()
            else:
                used_rule_fallback = True
                fallback_agent = GROQ.generate_rule_based_reply(
                    conversation,
                    intel,
                    intents=intents,
                )
                safe_agent = validate_agent_result(fallback_agent, reply, agent_notes)
                reply = safe_agent["reply"]
                agent_notes = safe_agent["agentNotes"]
                stop_reason = safe_agent["stopReason"]
        except Exception:
            LLM_CIRCUIT.record_failure()
            used_rule_fallback = True
            fallback_agent = GROQ.generate_rule_based_reply(
                conversation,
                intel,
                intents=intents,
            )
            safe_agent = validate_agent_result(fallback_agent, reply, agent_notes)
            reply = safe_agent["reply"]
            agent_notes = safe_agent["agentNotes"]
            stop_reason = safe_agent["stopReason"]
    elif scam_detected and policy_zone == "lethal":
        reply = "Security alert detected. I cannot proceed with this request."
        agent_notes = (agent_notes + "; lethal_zone_block").strip("; ")

    # Persist agent reply to keep session transcript and message counts consistent.
    append_message(
        DB,
        session_id,
        "user",
        reply,
        int(time.time() * 1000),
    )

    # Engagement completion rules
    session = get_or_create_session(DB, session_id)
    total_messages = int(session["total_messages"]) if "total_messages" in session.keys() else 0
    total_messages_exchanged = total_messages
    has_intel = any(intel.get(k) for k in ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers"])

    engagement_complete = False
    if total_messages >= 10:
        engagement_complete = True
    if total_messages >= 6 and has_intel:
        engagement_complete = True
    if stop_reason == "scammer_left":
        engagement_complete = True

    callback_pending = bool(session["callback_pending"]) if "callback_pending" in session.keys() else False
    should_attempt_callback = scam_detected and (engagement_complete or callback_pending) and not bool(
        session["engagement_complete"]
    )
    if should_attempt_callback:
        callback_notes = _competition_agent_notes(
            raw_notes=agent_notes,
            scam_detected=scam_detected,
            policy_zone=policy_zone,
            fallback_used=used_rule_fallback,
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
        fallbackUsed=used_rule_fallback,
        circuit=LLM_CIRCUIT.snapshot(),
        latencyMs=latency_ms,
        apiCalls=api_calls,
        totalMessages=total_messages_exchanged,
    )

    return MessageResponse(
        status="success",
        sessionId=session_id,
        reply=reply,
        scamDetected=scam_detected,
        shouldEngage=should_engage,
        extractedIntelligence=intel,
        agentNotes=_competition_agent_notes(
            raw_notes=agent_notes,
            scam_detected=scam_detected,
            policy_zone=policy_zone,
            fallback_used=used_rule_fallback,
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


def _normalize_session_id(value: str) -> str:
    # Keep session IDs URL-safe and bounded to avoid malformed IDs across clients.
    candidate = value.strip()
    if candidate and re.fullmatch(r"[A-Za-z0-9._-]{8,80}", candidate):
        return candidate
    return f"sess_{uuid.uuid4().hex[:20]}"


def _competition_agent_notes(
    *,
    raw_notes: str,
    scam_detected: bool,
    policy_zone: str,
    fallback_used: bool,
) -> str:
    lower = (raw_notes or "").lower()
    reasons: list[str] = []
    if "credential_harvest_signal" in lower:
        reasons.append("Credential harvesting intent detected")
    if "prompt_injection_signal" in lower:
        reasons.append("Prompt-injection style manipulation attempt detected")
    if "link_present" in lower:
        reasons.append("Message contains suspicious redirection behavior")
    if policy_zone == "lethal":
        reasons.append("Conversation reached lethal-risk policy zone")
    if fallback_used or "llm failure" in lower or "llm_layer_failed" in lower:
        reasons.append("Rule-based verification used due to LLM instability")
    if not reasons and scam_detected:
        reasons.append("Scam pattern detected from urgency and verification pressure")
    if not scam_detected:
        reasons.append("No high-confidence scam pattern detected in current conversation state")
    return "; ".join(reasons)
