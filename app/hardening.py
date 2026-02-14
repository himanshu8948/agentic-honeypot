import json
import logging
import threading
import time
from collections import deque
from typing import Any


logger = logging.getLogger("agentic_honeypot")


def setup_logging() -> None:
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, "ts": int(time.time())}
    payload.update(fields)
    try:
        logger.info(json.dumps(payload, ensure_ascii=True))
    except Exception:
        logger.info(f'{{"event":"{event}","ts":{int(time.time())},"log_error":true}}')


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 4, recovery_seconds: int = 45):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._failure_count = 0
        self._open_until = 0.0
        self._lock = threading.Lock()

    def allow_request(self) -> bool:
        with self._lock:
            now = time.time()
            if now < self._open_until:
                return False
            return True

    def record_success(self) -> None:
        with self._lock:
            self._failure_count = 0
            self._open_until = 0.0

    def record_failure(self) -> None:
        with self._lock:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._open_until = time.time() + self.recovery_seconds

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "failureCount": self._failure_count,
                "isOpen": time.time() < self._open_until,
                "openUntil": int(self._open_until),
            }


class SlidingWindowLimiter:
    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            cutoff = now - self.window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_requests:
                return False
            q.append(now)
            return True


def validate_llm_result(data: dict[str, Any] | None) -> dict[str, Any]:
    result = data or {}
    reasons = result.get("reasons", [])
    if not isinstance(reasons, list):
        reasons = []
    reasons = [str(r) for r in reasons if str(r)]

    confidence = 0.0
    try:
        confidence = float(result.get("confidence", 0.0))
    except Exception:
        confidence = 0.0
    confidence = min(1.0, max(0.0, confidence))

    category = str(result.get("intentCategory", "other"))
    if category not in {"phishing", "upi", "bank", "offer", "other"}:
        category = "other"

    return {
        "scamDetected": bool(result.get("scamDetected", False)),
        "confidence": confidence,
        "reasons": reasons,
        "intentCategory": category,
    }


def validate_agent_result(data: dict[str, Any] | None, fallback_reply: str, fallback_notes: str) -> dict[str, Any]:
    result = data or {}
    reply = str(result.get("reply", fallback_reply)).strip() or fallback_reply
    notes = str(result.get("agentNotes", fallback_notes)).strip() or fallback_notes
    stop_reason = result.get("stopReason")
    if stop_reason not in {"scammer_left", "intel_complete", None}:
        stop_reason = None
    return {"reply": reply, "agentNotes": notes, "stopReason": stop_reason}
