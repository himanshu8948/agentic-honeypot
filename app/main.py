import asyncio
import logging
import time
from typing import Any, Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .config import Settings, load_settings
from .db import (
    append_message,
    connect,
    count_messages,
    get_api_calls,
    get_or_create_session,
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
from .llm import GroqClient, pick_persona
from .templates import build_persona, build_safe_reply, choose_phase

app = FastAPI(title="himanshu_agentic_honeypot")

SETTINGS: Settings | None = None
DB = None
GROQ: GroqClient | None = None
logger = logging.getLogger("api")


class Message(BaseModel):
    sender: str = Field(..., pattern="^(scammer|user)$")
    text: str
    timestamp: int


class Metadata(BaseModel):
    channel: Optional[str] = None
    language: Optional[str] = None
    locale: Optional[str] = None


class MessageRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: list[Message] = Field(default_factory=list)
    metadata: Optional[Metadata] = None


class MessageResponse(BaseModel):
    status: str
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
    global SETTINGS, DB, GROQ
    SETTINGS = load_settings()
    DB = connect(SETTINGS.db_path)
    init_db(DB)
    if SETTINGS.use_llm:
        GROQ = GroqClient(
            base_url=SETTINGS.groq_base_url,
            api_keys=SETTINGS.groq_api_keys,
            model=SETTINGS.groq_model,
        )


@app.post("/api/message", response_model=MessageResponse)
async def handle_message(payload: MessageRequest, _auth: None = Depends(require_api_key)) -> MessageResponse:
    if SETTINGS is None or DB is None:
        raise HTTPException(status_code=500, detail="Service not initialized")

    session = get_or_create_session(DB, payload.sessionId)
    increment_api_calls(DB, payload.sessionId)
    if int(session["total_messages"]) == 0 and payload.conversationHistory:
        for msg in payload.conversationHistory:
            append_message(DB, payload.sessionId, msg.sender, msg.text, msg.timestamp)

    inferred_sender = infer_sender_role(payload.message.text)
    effective_sender = payload.message.sender
    if inferred_sender != payload.message.sender:
        effective_sender = inferred_sender

    append_message(DB, payload.sessionId, effective_sender, payload.message.text, payload.message.timestamp)

    intel = load_intel(DB, payload.sessionId)
    user_intel = load_user_intel(DB, payload.sessionId)

    # Extract from provided conversation history as well (scammer only)
    if payload.conversationHistory:
        for msg in payload.conversationHistory:
            if msg.sender == "scammer":
                intel = extract_intel(msg.text, intel)
            else:
                user_intel = extract_intel(msg.text, user_intel)

    if effective_sender == "scammer":
        intel = extract_intel(payload.message.text, intel)
    else:
        user_intel = extract_intel(payload.message.text, user_intel)

    # Remove any identifiers previously seen in user messages
    intel["upiIds"] = [x for x in intel["upiIds"] if x not in user_intel.get("upiIds", [])]
    intel["phoneNumbers"] = [x for x in intel["phoneNumbers"] if x not in user_intel.get("phoneNumbers", [])]
    intel["bankAccounts"] = [x for x in intel["bankAccounts"] if x not in user_intel.get("bankAccounts", [])]
    intel["phishingLinks"] = [x for x in intel["phishingLinks"] if x not in user_intel.get("phishingLinks", [])]

    save_intel(DB, payload.sessionId, intel)
    save_user_intel(DB, payload.sessionId, user_intel)

    score = rule_score(payload.message.text)
    intent_score = intent_signal_score(payload.message.text)
    combined_score = score + intent_score

    scam_detected = False
    confidence = 0.0
    agent_notes = ""
    intents = {"intentScammer": "", "intentUser": ""}
    conversation_summary = session["conversation_summary"] if "conversation_summary" in session.keys() else ""
    total_messages = int(session["total_messages"])
    last_reply = session["last_reply"] if "last_reply" in session.keys() else None
    persona = session["persona"] if "persona" in session.keys() else None
    if not persona:
        persona = build_persona()

    if SETTINGS.use_llm and GROQ is not None:
        try:
            recent_messages = list_messages(DB, payload.sessionId, limit=24)
            context = "\n".join([f"{m['sender']}: {m['text']}" for m in recent_messages])
            intents = await GROQ.summarize_intents(recent_messages)
            if int(session["total_messages"]) % 6 == 0:
                conversation_summary = await GROQ.summarize_conversation(
                    recent_messages[-12:],
                    conversation_summary,
                )
            context = f"Summary: {conversation_summary}\n\n{context}" if conversation_summary else context
            if combined_score >= SETTINGS.rule_threshold + 4:
                llm_result = {"scamDetected": True, "confidence": 0.99, "reasons": ["strong_rule_match"]}
            else:
                llm_result = await GROQ.classify(payload.message.text, context=context, intents=intents)
            if combined_score >= SETTINGS.rule_threshold + 2 and float(llm_result.get("confidence", 0.0)) < 0.6:
                llm_result["confidence"] = 0.6
            scam_detected = bool(llm_result.get("scamDetected", False))
            confidence = float(llm_result.get("confidence", 0.0))
            agent_notes = "; ".join(llm_result.get("reasons", []))
        except Exception as exc:
            logger.exception("LLM classify failed: %s", exc)
            llm_result = {"scamDetected": False, "confidence": 0.0, "reasons": []}
    else:
        llm_result = {"scamDetected": False, "confidence": 0.0, "reasons": []}

    if combined_score >= SETTINGS.rule_threshold or confidence >= SETTINGS.llm_threshold:
        scam_detected = True

    should_engage = scam_detected and effective_sender == "scammer"

    reply = "Thanks. Can you share more details?"
    stop_reason = None
    if should_engage:
        conversation = list_messages(DB, payload.sessionId, limit=24)
        persona = pick_persona() if SETTINGS.use_llm else persona
        if SETTINGS.use_llm and GROQ is not None:
            try:
                agent = await GROQ.generate_reply(
                    persona,
                    conversation,
                    intel,
                    intents=intents,
                    suspected_scammer=True,
                    last_reply=last_reply,
                )
                reply = _dedupe_reply(str(agent.get("reply", reply)), last_reply)
                agent_notes = str(agent.get("agentNotes", agent_notes))
                stop_reason = agent.get("stopReason")
            except Exception as exc:
                logger.exception("LLM reply failed: %s", exc)
                reply = _fallback_reply(intel, last_reply, payload.message.text, total_messages)
                agent_notes = (
                    "LLM failure; "
                    + _build_agent_notes(
                        intel,
                        combined_score,
                        intent_score,
                        score,
                        effective_sender,
                    )
                )
        else:
            reply = _fallback_reply(intel, last_reply, payload.message.text, total_messages)
            agent_notes = _build_agent_notes(
                intel,
                combined_score,
                intent_score,
                score,
                effective_sender,
            )

    # Store the agent reply as a user message for accurate total_messages
    if reply:
        append_message(
            DB,
            payload.sessionId,
            "user",
            reply,
            int(time.time() * 1000),
        )

    # Normalize agent notes for hackathon format (behavior + intent signals)
    if scam_detected:
        agent_notes = _build_agent_notes(
            intel,
            combined_score,
            intent_score,
            score,
            effective_sender,
        ).strip()

    # Engagement completion rules
    stored_count = count_messages(DB, payload.sessionId)
    api_calls = get_api_calls(DB, payload.sessionId)
    history_count = len(payload.conversationHistory) if payload.conversationHistory else 0
    computed_count = history_count + 1 + (1 if reply else 0)
    total_messages = max(stored_count, computed_count, api_calls * 2)
    has_intel = any(intel.get(k) for k in ["bankAccounts", "upiIds", "phishingLinks", "phoneNumbers"])

    engagement_complete = False
    if total_messages >= 6:
        engagement_complete = True
    if total_messages >= 4 and has_intel:
        engagement_complete = True
    if stop_reason == "scammer_left":
        engagement_complete = True

    callback_pending = bool(session["callback_pending"]) if "callback_pending" in session.keys() else False
    should_attempt_callback = scam_detected and (engagement_complete or callback_pending) and not bool(
        session["engagement_complete"]
    )
    if should_attempt_callback:
        success = await _send_callback(
            SETTINGS,
            payload.sessionId,
            scam_detected,
            total_messages,
            intel,
            agent_notes,
        )
        if not success:
            engagement_complete = False
            callback_pending = True
            agent_notes = (agent_notes + " | callback_failed").strip(" |")
        else:
            callback_pending = False

    update_session(
        DB,
        payload.sessionId,
        scam_detected,
        confidence,
        reply,
        engagement_complete,
        agent_notes,
        callback_pending,
        conversation_summary,
        persona,
    )

    return MessageResponse(
        status="success",
        reply=reply,
        scamDetected=scam_detected,
        shouldEngage=should_engage,
        extractedIntelligence=intel,
        agentNotes=agent_notes,
    )


@app.post("/analyze", response_model=MessageResponse)
async def analyze_alias(payload: MessageRequest, _auth: None = Depends(require_api_key)) -> MessageResponse:
    return await handle_message(payload, _auth)


async def _send_callback(
    settings: Settings,
    session_id: str,
    scam_detected: bool,
    total_messages: int,
    intel: dict[str, list[str]],
    agent_notes: str,
) -> bool:
    payload = {
        "sessionId": session_id,
        "scamDetected": scam_detected,
        "totalMessagesExchanged": total_messages,
        "extractedIntelligence": intel,
        "agentNotes": agent_notes,
    }

    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(settings.guvi_callback_url, json=payload)
                if 200 <= resp.status_code < 300:
                    return True
        except Exception:
            pass
        await asyncio.sleep(2 ** attempt)
    return False


def _fallback_reply(
    intel: dict[str, list[str]],
    last_reply: str | None,
    last_scam_text: str,
    total_messages: int,
) -> str:
    phase = choose_phase(total_messages, last_scam_text)
    if last_reply and phase == "payment_path":
        lower = last_reply.lower()
        if any(k in lower for k in ["exact", "handle", "destination", "number", "upi"]):
            phase = "clarification"
    return build_safe_reply(phase, last_reply)


def _dedupe_reply(reply: str, last_reply: str | None) -> str:
    if not last_reply:
        return reply
    if reply.strip().lower() == last_reply.strip().lower():
        return "Just to be sure, can you share the official steps and a reference ID?"
    return reply


def _build_agent_notes(
    intel: dict[str, list[str]],
    combined_score: int,
    intent_score: int,
    rule_score_value: int,
    inferred_sender: str,
) -> str:
    signals = [s.lower() for s in intel.get("suspiciousKeywords", [])]
    urgency = any(k in signals for k in ["urgent", "immediately", "account blocked", "account suspended", "account freeze"])
    payment_redirection = bool(intel.get("upiIds") or intel.get("phoneNumbers") or intel.get("phishingLinks"))

    extracted = []
    if intel.get("upiIds"):
        extracted.append("UPI IDs")
    if intel.get("phoneNumbers"):
        extracted.append("phone numbers")
    if intel.get("bankAccounts"):
        extracted.append("bank accounts")
    if intel.get("phishingLinks"):
        extracted.append("links")
    extracted_text = ", ".join(extracted) if extracted else "no identifiers yet"

    tactics = []
    if urgency:
        tactics.append("urgency tactics")
    if payment_redirection:
        tactics.append("payment redirection")
    tactics_text = " and ".join(tactics) if tactics else "suspicious messaging"

    return f"Scammer used {tactics_text}."
