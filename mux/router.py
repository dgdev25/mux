import re
from mux.config import load_config
from mux.ledger import append_run
from mux.local_runtime import ensure_local_runtime
from mux.metrics import increment, ratio_local_impl
from mux.policies.escalation import should_escalate
from mux.providers.local_executor import run_local_executor
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
    return re.search(r"/[^\s]+", task) is not None


def _run_persistence_workflow(task: str, cfg: dict) -> dict:
    local_ok, local_status = ensure_local_runtime(cfg)
    if not local_ok:
        if not cfg.get("workflow", {}).get("allow_sota_write_fallback", True):
            return {
                "route": "none",
                "result": run_local_executor(task, cfg),
                "verify": verify("", cfg),
                "reason": f"local_runtime_unavailable:{local_status}",
                "runtime_status": local_status,
                "retries": 0,
            }
    wcfg = cfg.get("workflow", {})
    run_review = bool(wcfg.get("run_sota_review", True))
    allow_sota_write_fallback = bool(wcfg.get("allow_sota_write_fallback", True))
    local_apply_review = bool(wcfg.get("local_apply_review", True))
    target_ratio = float(wcfg.get("target_local_implementation_ratio", 0.95))

    local = run_local_executor(task, cfg)
    if not local.output.startswith("LOCAL_EXECUTOR_ERROR"):
        stats = increment("local_impl_tasks", 1)
        v_local = verify(local.output, cfg)

        review_text = ""
        if run_review:
            review = run_sota(
                task="Peer-review this implementation. Focus on correctness, bugs, tests, and minimal fixes.",
                context=f"task={task}\nimplementation_summary={local.output}",
                cfg=cfg,
            )
            increment("sota_review_tasks", 1)
            review_text = review.output if not review.output.startswith("SOTA_PROVIDER_ERROR") else ""

        if local_apply_review and review_text:
            patched = run_local_executor(task, cfg, review_feedback=review_text)
            if not patched.output.startswith("LOCAL_EXECUTOR_ERROR"):
                increment("local_impl_tasks", 1)
                v = verify(patched.output, cfg)
                return {
                    "route": "local_executor",
                    "result": patched,
                    "verify": v,
                    "reason": "local_impl_plus_sota_review",
                    "runtime_status": local_status,
                    "retries": 0,
                    "local_impl_ratio": ratio_local_impl(stats),
                }

        return {
            "route": "local_executor",
            "result": local,
            "verify": v_local,
            "reason": "local_impl",
            "runtime_status": local_status,
            "retries": 0,
            "local_impl_ratio": ratio_local_impl(stats),
        }

    if allow_sota_write_fallback:
        sota_exec = run_executor(task, cfg)
        if not sota_exec.output.startswith("EXECUTOR_ERROR"):
            stats = increment("sota_write_tasks", 1)
            v = verify(sota_exec.output, cfg)
            reason = "sota_write_fallback"
            if ratio_local_impl(stats) < target_ratio:
                reason += f";ratio_below_target:{ratio_local_impl(stats):.2f}"
            return {
                "route": "executor",
                "result": sota_exec,
                "verify": v,
                "reason": reason,
                "runtime_status": local_status,
                "retries": 0,
                "local_impl_ratio": ratio_local_impl(stats),
            }

    return {
        "route": "none",
        "result": local,
        "verify": verify("", cfg),
        "reason": "local_executor_failed_and_no_fallback",
        "runtime_status": local_status,
        "retries": 0,
    }


def run(task: str) -> dict:
    cfg = load_config()
    runtime_status = "not_checked"

    if _requires_persistence(task):
        out = _run_persistence_workflow(task, cfg)
        run_id = append_run(task=task, out=out, runtime_status=out.get("runtime_status", "persistence_flow"), cfg=cfg)
        out["run_id"] = run_id
        return out

    rcfg = cfg["router"]
    max_retries = int(rcfg.get("max_local_retries", 2))
    keywords = rcfg.get("complexity_keywords", [])
    min_conf = float(rcfg.get("local_confidence_threshold", 0.72))

    local_ok, local_status = ensure_local_runtime(cfg)
    runtime_status = local_status

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
            out = {
                "route": "local",
                "result": local,
                "verify": v,
                "reason": "",
                "retries": retries,
            }
            run_id = append_run(task=task, out=out, runtime_status=runtime_status, cfg=cfg)
            out["run_id"] = run_id
            return out

        sota = run_sota(task=task, context=f"local={local.output}\nverify={v.summary}\nreason={reason}", cfg=cfg)
        if sota.output.startswith("SOTA_PROVIDER_ERROR"):
            out = {
                "route": "local",
                "result": local,
                "verify": v,
                "reason": f"{reason}; sota_unavailable",
                "retries": retries,
            }
            run_id = append_run(task=task, out=out, runtime_status=runtime_status, cfg=cfg)
            out["run_id"] = run_id
            return out

        v2 = verify(sota.output, cfg)
        out = {
            "route": "sota",
            "result": sota,
            "verify": v2,
            "reason": reason,
            "retries": retries,
        }
        run_id = append_run(task=task, out=out, runtime_status=runtime_status, cfg=cfg)
        out["run_id"] = run_id
        return out

    sota = run_sota(task=task, context=f"local_runtime={local_status}", cfg=cfg)
    if sota.output.startswith("SOTA_PROVIDER_ERROR"):
        out = {
            "route": "none",
            "result": sota,
            "verify": verify("", cfg),
            "reason": f"local_down_and_sota_unavailable:{local_status}",
            "retries": retries,
        }
        run_id = append_run(task=task, out=out, runtime_status=runtime_status, cfg=cfg)
        out["run_id"] = run_id
        return out

    out = {
        "route": "sota",
        "result": sota,
        "verify": verify(sota.output, cfg),
        "reason": f"local_unavailable:{local_status}",
        "retries": retries,
    }
    run_id = append_run(task=task, out=out, runtime_status=runtime_status, cfg=cfg)
    out["run_id"] = run_id
    return out
