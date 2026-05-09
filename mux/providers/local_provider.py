import json
import os
import urllib.request
from mux.types import ModelResult


def chat_local(system_prompt: str, user_prompt: str, cfg: dict, *, max_tokens: int | None = None, temperature: float | None = None) -> ModelResult:
    p = cfg["providers"]["local"]
    base_url = p["base_url"].rstrip("/")
    model = p["model"]
    key = os.getenv(p.get("api_key_env", "LOCAL_OPENAI_API_KEY"), "")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": float(p.get("temperature", 0.2) if temperature is None else temperature),
        "max_tokens": int(p.get("max_tokens", 1200) if max_tokens is None else max_tokens),
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
        with urllib.request.urlopen(req, timeout=180) as r:
            body = json.loads(r.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        finish = body["choices"][0].get("finish_reason", "")
        conf = 0.8 if finish in ("stop", "length") and len(content) > 80 else 0.62
        return ModelResult(model=f"local:{model}", output=content, confidence=conf)
    except Exception as e:
        return ModelResult(model=f"local:{model}", output=f"LOCAL_PROVIDER_ERROR: {e}", confidence=0.1)


def run_local(task: str, cfg: dict) -> ModelResult:
    return chat_local(
        system_prompt="You are a coding assistant. Be concise and actionable.",
        user_prompt=task,
        cfg=cfg,
    )
