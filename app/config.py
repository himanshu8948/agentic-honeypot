import os
from dataclasses import dataclass


def _get_env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


@dataclass(frozen=True)
class Settings:
    service_api_key: str
    db_path: str
    rule_threshold: int
    guvi_callback_url: str
    trusted_sms_headers: set[str]
    firebase_enabled: bool
    firebase_project_id: str | None
    # Engagement/callback pacing knobs (defaults are conservative for most demos)
    target_messages_exchanged: int
    min_messages_before_complete: int
    min_messages_before_complete_with_intel: int


def load_settings() -> Settings:
    service_api_key = _get_env("SERVICE_API_KEY")
    if not service_api_key:
        raise RuntimeError("SERVICE_API_KEY is required")

    db_path = _get_env("DB_PATH", "./honeypot.db")
    firebase_enabled = _get_bool_env("FIREBASE_ENABLED", False)
    firebase_project_id = _get_env("FIREBASE_PROJECT_ID")

    rule_threshold = int(_get_env("RULE_THRESHOLD", "8"))

    guvi_callback_url = _get_env(
        "GUVI_CALLBACK_URL",
        "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
    )
    trusted_sms_headers = _load_trusted_headers()

    # Default to hackathon-style long engagements; override in env for shorter demos.
    target_messages_exchanged = int(_get_env("TARGET_MESSAGES_EXCHANGED", "150"))
    min_messages_before_complete = int(_get_env("MIN_MESSAGES_BEFORE_COMPLETE", "10"))
    min_messages_before_complete_with_intel = int(_get_env("MIN_MESSAGES_BEFORE_COMPLETE_WITH_INTEL", "6"))

    return Settings(
        service_api_key=service_api_key,
        db_path=db_path,
        rule_threshold=rule_threshold,
        guvi_callback_url=guvi_callback_url,
        trusted_sms_headers=trusted_sms_headers,
        firebase_enabled=firebase_enabled,
        firebase_project_id=firebase_project_id,
        target_messages_exchanged=max(0, target_messages_exchanged),
        min_messages_before_complete=max(1, min_messages_before_complete),
        min_messages_before_complete_with_intel=max(1, min_messages_before_complete_with_intel),
    )

def _load_trusted_headers() -> set[str]:
    headers: set[str] = set()
    csv_headers = _get_env("TRUSTED_SMS_HEADERS", "")
    if csv_headers:
        for h in csv_headers.split(","):
            v = h.strip().upper()
            if v:
                headers.add(v)

    file_path = _get_env("TRUSTED_SMS_HEADERS_PATH")
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    v = line.strip().upper()
                    if v and not v.startswith("#"):
                        headers.add(v)
        except OSError:
            pass

    return headers


def _get_bool_env(name: str, default: bool) -> bool:
    raw = _get_env(name)
    if raw is None:
        return default
    v = raw.strip().lower()
    return v in {"1", "true", "yes", "on"}
