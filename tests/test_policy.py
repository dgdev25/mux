from mux.policies.escalation import should_escalate


def test_low_confidence_escalates():
    esc, reason = should_escalate("simple task", 0.2, True, 0, 2, [])
    assert esc is True
    assert reason == "low_confidence"
