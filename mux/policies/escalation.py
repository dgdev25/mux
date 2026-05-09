def complexity_score(task: str, keywords: list[str]) -> int:
    t = task.lower()
    return sum(1 for k in keywords if k in t)


def should_escalate(task: str, confidence: float, min_confidence: float, verify_ok: bool, retries: int, max_retries: int, keywords: list[str]) -> tuple[bool, str]:
    if confidence < min_confidence:
        return True, "low_confidence"
    if not verify_ok and retries >= max_retries:
        return True, "verification_failures"
    if complexity_score(task, keywords) >= 2:
        return True, "high_complexity"
    return False, ""
