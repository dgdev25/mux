import re
from mux.config import load_config
from mux.local_runtime import ensure_local_runtime
from mux.policies.escalation import should_escalate
from mux.providers.local_provider import run_local
from mux.providers.sota_provider import run_sota, run_executor
from mux.verifier import verify


PERSISTENCE_HINTS = (
    "create", "build", "scaffold", "implement", "write files", "generate", "set up", "setup",
    "in /", "under /", "at /", "project in", "make a project", "on disk", "persist"
)


def _requires_persistence(task: str) -> bool:
    t = task.lower()
    if any(k in t for k in PERSISTENCE_HINTS):
        return True
    # Any explicit absolute path strongly suggests file operations.
    return re.search(r"/[^\s]+", task) is not None


def run(task: str) -> dict:
    cfg = load_config()

    # Critical bug fix: persistence tasks must run an executor, not advisory text generation.
    if _requires_persistence(task):
        exec_result = run_executor(task, cfg)
        v = verify(exec_result.output, cfg)
        route = "executor" if not exec_result.output.startswith("EXECUTOR_ERROR") else "none"
        reason = "persistence_task" if route == "executor" else "executor_unavailable"
        return {
            "route": route,
            "result": exec_result,
            "verify": v,
            "reason": reason,
            "retries": 0,
        }

    rcfg = cfg["router"]
    max_retries = int(rcfg.get("max_local_retries", 2))
    keywords = rcfg.get("complexity_keywords", [])
    min_conf = float(rcfg.get("local_confidence_threshold", 0.72))

    local_ok, local_status = ensure_local_runtime(cfg)

    retries = 0
    if local_ok:
        local = run_local(task, cfg)
        v = verify(local.output, cfg)

        while (not v.ok) and retries < max_retries:
            retries += 1
            local = run_local(task + "\n\nPrevious attempt failed verification. Improve correctness.", cfg)
            v = verify(local.output, cfg)

        escalate, reason = should_escalate(
            task=task,
            confidence=local.confidence,
            min_confidence=min_conf,
            verify_ok=v.ok,
            retries=retries,
            max_retries=max_retries,
            keywords=keywords,
        )

        if not escalate:
            return {
                "route": "local",
                "result": local,
                "verify": v,
                "reason": "",
                "retries": retries,
            }

        sota = run_sota(task=task, context=f"local={local.output}\nverify={v.summary}\nreason={reason}", cfg=cfg)
        if sota.output.startswith("SOTA_PROVIDER_ERROR"):
            return {
                "route": "local",
                "result": local,
                "verify": v,
                "reason": f"{reason}; sota_unavailable",
                "retries": retries,
            }

        v2 = verify(sota.output, cfg)
        return {
            "route": "sota",
            "result": sota,
            "verify": v2,
            "reason": reason,
            "retries": retries,
        }

    sota = run_sota(task=task, context=f"local_runtime={local_status}", cfg=cfg)
    if sota.output.startswith("SOTA_PROVIDER_ERROR"):
        return {
            "route": "none",
            "result": sota,
            "verify": verify("", cfg),
            "reason": f"local_down_and_sota_unavailable:{local_status}",
            "retries": retries,
        }

    return {
        "route": "sota",
        "result": sota,
        "verify": verify(sota.output, cfg),
        "reason": f"local_unavailable:{local_status}",
        "retries": retries,
    }
