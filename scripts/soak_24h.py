from __future__ import annotations

import argparse
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Run long soak test against /analyze")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--api-key", default="dev-key")
    p.add_argument("--hours", type=float, default=24.0)
    p.add_argument("--concurrency", type=int, default=8)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--session-pool", type=int, default=40)
    p.add_argument("--timeout", type=float, default=12.0)
    p.add_argument("--report-every-sec", type=int, default=60)
    return p.parse_args()


SCAMMER_MSGS = [
    "URGENT: account blocked. Send OTP now.",
    "Share exact UPI handle and pay verification fee immediately.",
    "Call this number now +91-9000011111 for immediate unfreeze.",
    "Click this link now: https://secure-verify.example.com/kyc",
    "Send account number and IFSC for urgent verification.",
]


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    arr = sorted(values)
    idx = int((p / 100.0) * (len(arr) - 1))
    return arr[idx]


def main() -> None:
    args = parse_args()
    end_at = time.time() + args.hours * 3600.0
    headers = {"x-api-key": args.api_key}
    sessions = [f"soak24-{i}" for i in range(max(1, args.session_pool))]

    ok = 0
    err = 0
    llm = 0
    fallback = 0
    status_counts: dict[int, int] = {}
    lats: list[float] = []
    last_report = time.time()

    def do_one(i: int) -> tuple[bool, int, bool, float]:
        sid = sessions[i % len(sessions)]
        payload = {
            "sessionId": sid,
            "message": {
                "sender": "scammer",
                "text": random.choice(SCAMMER_MSGS),
                "timestamp": int(time.time() * 1000),
            },
            "conversationHistory": [],
            "metadata": {"platform": "sms", "language": "", "locale": "IN"},
        }
        t0 = time.time()
        with httpx.Client(timeout=args.timeout) as client:
            r = client.post(f"{args.base_url}/analyze", json=payload, headers=headers)
        dt_ms = (time.time() - t0) * 1000.0
        if r.status_code != 200:
            return False, r.status_code, False, dt_ms
        data = r.json()
        notes = str(data.get("agentNotes") or "")
        return True, 200, ("llm_reply:groq" in notes), dt_ms

    i = 0
    while time.time() < end_at:
        with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as ex:
            futures = [ex.submit(do_one, i + j) for j in range(max(1, args.batch_size))]
            for f in as_completed(futures):
                try:
                    success, status, used_llm, dt_ms = f.result()
                except Exception:
                    success, status, used_llm, dt_ms = False, 0, False, 0.0
                lats.append(dt_ms)
                if success:
                    ok += 1
                    if used_llm:
                        llm += 1
                    else:
                        fallback += 1
                else:
                    err += 1
                    status_counts[status] = status_counts.get(status, 0) + 1
        i += args.batch_size

        now = time.time()
        if now - last_report >= max(5, args.report_every_sec):
            p50 = percentile(lats, 50)
            p95 = percentile(lats, 95)
            p99 = percentile(lats, 99)
            total = ok + err
            print(
                {
                    "total": total,
                    "ok": ok,
                    "err": err,
                    "llm": llm,
                    "fallback": fallback,
                    "ok_rate": round((ok / total) if total else 0.0, 4),
                    "p50_ms": round(p50, 1),
                    "p95_ms": round(p95, 1),
                    "p99_ms": round(p99, 1),
                    "status_counts": status_counts,
                }
            )
            last_report = now

    p50 = percentile(lats, 50)
    p95 = percentile(lats, 95)
    p99 = percentile(lats, 99)
    total = ok + err
    print("FINAL", {
        "total": total,
        "ok": ok,
        "err": err,
        "llm": llm,
        "fallback": fallback,
        "ok_rate": round((ok / total) if total else 0.0, 4),
        "p50_ms": round(p50, 1),
        "p95_ms": round(p95, 1),
        "p99_ms": round(p99, 1),
        "status_counts": status_counts,
    })


if __name__ == "__main__":
    main()
