import json
import math
import os
import re
from dataclasses import dataclass


_TOKEN_RE = re.compile(r"[a-z0-9@._/-]{2,}", re.IGNORECASE)


@dataclass(frozen=True)
class StatModel:
    # Naive Bayes log-probabilities for tokens conditioned on class.
    log_prior_scam: float
    log_prior_ham: float
    logp_token_scam: dict[str, float]
    logp_token_ham: dict[str, float]
    logp_unk_scam: float
    logp_unk_ham: float

    def predict_proba_scam(self, text: str) -> float:
        tokens = _TOKEN_RE.findall(text.lower())
        log_scam = self.log_prior_scam
        log_ham = self.log_prior_ham
        for t in tokens:
            log_scam += self.logp_token_scam.get(t, self.logp_unk_scam)
            log_ham += self.logp_token_ham.get(t, self.logp_unk_ham)
        # stable softmax for 2 classes
        m = max(log_scam, log_ham)
        ps = math.exp(log_scam - m)
        ph = math.exp(log_ham - m)
        return ps / (ps + ph)


def load_stat_model() -> StatModel | None:
    path = os.getenv("STAT_MODEL_PATH", "").strip() or "./models/scam_nb.json"
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return StatModel(
            log_prior_scam=float(data["log_prior_scam"]),
            log_prior_ham=float(data["log_prior_ham"]),
            logp_token_scam={str(k): float(v) for k, v in (data.get("logp_token_scam") or {}).items()},
            logp_token_ham={str(k): float(v) for k, v in (data.get("logp_token_ham") or {}).items()},
            logp_unk_scam=float(data["logp_unk_scam"]),
            logp_unk_ham=float(data["logp_unk_ham"]),
        )
    except Exception:
        return None

