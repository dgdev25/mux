"""CLI entrypoint for the scientific calculator."""

from __future__ import annotations

import argparse

from .evaluator import EvaluationError, evaluate_expression


def _run_once(expression: str) -> int:
    try:
        result = evaluate_expression(expression)
    except EvaluationError as exc:
        print(f"error: {exc}")
        return 1
    print(result)
    return 0


def _run_repl() -> int:
    print("Scientific Calculator REPL. Type 'quit' or 'exit' to leave.")
    while True:
        try:
            expression = input("> ").strip()
        except EOFError:
            print()
            return 0

        if expression.lower() in {"quit", "exit"}:
            return 0
        if not expression:
            continue

        _run_once(expression)


def main() -> int:
    parser = argparse.ArgumentParser(description="Safe scientific calculator")
    parser.add_argument("expression", nargs="?", help="Expression to evaluate")
    args = parser.parse_args()

    if args.expression is not None:
        return _run_once(args.expression)

    return _run_repl()


if __name__ == "__main__":
    raise SystemExit(main())
