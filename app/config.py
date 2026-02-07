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
    groq_api_keys: list[str]
    groq_model: str
    groq_base_url: str
    llm_provider: str
    google_api_key: str | None
    gemini_model: str
    gemini_base_url: str
    use_llm: bool
    db_path: str
    rule_threshold: int
    llm_threshold: float
    guvi_callback_url: str


def load_settings() -> Settings:
    service_api_key = _get_env("SERVICE_API_KEY")
    if not service_api_key:
        raise RuntimeError("SERVICE_API_KEY is required")

    use_llm = _get_env("USE_LLM", "0").lower() in {"1", "true", "yes"}
    llm_provider = (_get_env("LLM_PROVIDER", "deepseek") or "deepseek").lower()

    groq_api_keys: list[str] = []
    if use_llm and llm_provider not in {"gemini"}:
        if llm_provider == "groq":
            groq_key = _get_env("GROQ_API_KEY")
            if not groq_key:
                raise RuntimeError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
            groq_api_keys = [groq_key]
        else:
            deepseek_api_key = _get_env("agentic_key")
            if not deepseek_api_key:
                raise RuntimeError("agentic_key is required when USE_LLM=1 and LLM_PROVIDER=deepseek")
            groq_api_keys = [deepseek_api_key]

    groq_model = _get_env("DEEPSEEK_MODEL", "deepseek-chat")
    groq_base_url = _get_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    if llm_provider == "groq":
        groq_model = _get_env("GROQ_MODEL", "mistral-7b-instruct")
        groq_base_url = _get_env("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    google_api_key = _get_env("GOOGLE_API_KEY")
    gemini_model = _get_env("GEMINI_MODEL", "gemini-2.0-flash")
    gemini_base_url = _get_env("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
    db_path = _get_env("DB_PATH", "./himanshu_agentic_honeypot.db")

    rule_threshold = int(_get_env("RULE_THRESHOLD", "3"))
    llm_threshold = float(_get_env("LLM_THRESHOLD", "0.6"))

    guvi_callback_url = _get_env(
        "GUVI_CALLBACK_URL",
        "https://hackathon.guvi.in/api/updateHoneyPotFinalResult",
    )

    return Settings(
        service_api_key=service_api_key,
        groq_api_keys=groq_api_keys,
        groq_model=groq_model,
        groq_base_url=groq_base_url,
        llm_provider=llm_provider,
        google_api_key=google_api_key,
        gemini_model=gemini_model,
        gemini_base_url=gemini_base_url,
        use_llm=use_llm,
        db_path=db_path,
        rule_threshold=rule_threshold,
        llm_threshold=llm_threshold,
        guvi_callback_url=guvi_callback_url,
    )
