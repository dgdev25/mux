import json

from mux.config import project_root


METRICS_PATH = project_root() / "logs" / "mux_metrics.json"


def _load() -> dict:
    if not METRICS_PATH.exists():
        return {
            "local_impl_tasks": 0,
            "sota_review_tasks": 0,
            "sota_write_tasks": 0,
        }
    try:
        return json.loads(METRICS_PATH.read_text())
    except Exception:
        return {
            "local_impl_tasks": 0,
            "sota_review_tasks": 0,
            "sota_write_tasks": 0,
        }


def increment(key: str, n: int = 1) -> dict:
    data = _load()
    data[key] = int(data.get(key, 0)) + n
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    METRICS_PATH.write_text(json.dumps(data, indent=2))
    return data


def ratio_local_impl(data: dict | None = None) -> float:
    d = data or _load()
    local = int(d.get("local_impl_tasks", 0))
    sota_write = int(d.get("sota_write_tasks", 0))
    total_impl = local + sota_write
    if total_impl == 0:
        return 1.0
    return local / total_impl
