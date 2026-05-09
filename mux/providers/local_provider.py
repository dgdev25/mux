import json
import os
import urllib.request
from mux.types import ModelResult


def run_local(task: str, cfg: dict) -> ModelResult:
    p = cfg["providers"]["local"]
    base_url = p["base_url"].rstrip("/")
    model = p["model"]
    key = os.getenv(p.get("api_key_env", "LOCAL_OPENAI_API_KEY"), "")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a coding assistant. Be concise and actionable."},
            {"role": "user", "content": task},
        ],
        "temperature": float(p.get("temperature", 0.2)),
        "max_tokens": int(p.get("max_tokens", 1200)),
    }

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {key}"} if key else {}),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            body = json.loads(r.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        # crude confidence heuristic from finish reason and response size
        finish = body["choices"][0].get("finish_reason", "")
        conf = 0.8 if finish in ("stop", "length") and len(content) > 80 else 0.62
        return ModelResult(model=f"local:{model}", output=content, confidence=conf)
    except Exception as e:
        return ModelResult(model=f"local:{model}", output=f"LOCAL_PROVIDER_ERROR: {e}", confidence=0.1)
