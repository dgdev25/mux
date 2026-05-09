from __future__ import annotations

import math

import pytest

from scientific_calculator.evaluator import EvaluationError, evaluate_expression


def test_basic_arithmetic() -> None:
    assert evaluate_expression("2 + 3 * 4") == 14.0


def test_parentheses_and_power() -> None:
    assert evaluate_expression("(2 + 3) ** 2") == 25.0


def test_functions_and_constants() -> None:
    value = evaluate_expression("sin(pi/2) + sqrt(16)")
    assert value == pytest.approx(5.0)


def test_log_function_with_base() -> None:
    assert evaluate_expression("log(8, 2)") == pytest.approx(3.0)


def test_unary() -> None:
    assert evaluate_expression("-3 + +2") == -1.0


def test_empty_expression_rejected() -> None:
    with pytest.raises(EvaluationError):
        evaluate_expression("   ")


def test_unknown_identifier_rejected() -> None:
    with pytest.raises(EvaluationError):
        evaluate_expression("x + 1")


def test_unsafe_attribute_access_rejected() -> None:
    with pytest.raises(EvaluationError):
        evaluate_expression("().__class__.__mro__")


def test_unsafe_function_rejected() -> None:
    with pytest.raises(EvaluationError):
        evaluate_expression("__import__('os').system('echo bad')")


def test_syntax_error_rejected() -> None:
    with pytest.raises(EvaluationError):
        evaluate_expression("2 +")


def test_domain_error_wrapped() -> None:
    with pytest.raises(EvaluationError):
        evaluate_expression("sqrt(-1)")


def test_factorial() -> None:
    assert evaluate_expression("factorial(5)") == math.factorial(5)
