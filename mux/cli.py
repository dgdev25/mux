import argparse
from mux.router import run
from mux.doctor import run_doctor


def main() -> None:
    parser = argparse.ArgumentParser(prog="mux")
    sub = parser.add_subparsers(dest="cmd", required=True)

    run_cmd = sub.add_parser("run", help="Run router on a task")
    run_cmd.add_argument("--task", required=True)

    sub.add_parser("doctor", help="Check local runtime and CLI provider health")

    args = parser.parse_args()

    if args.cmd == "run":
        out = run(args.task)
        print(f"route: {out['route']}")
        print(f"model: {out['result'].model}")
        print(f"reason: {out['reason'] or 'n/a'}")
        print(f"run_id: {out.get('run_id', 'n/a')}")
        print(f"retries: {out['retries']}")
        print(f"verify: {'pass' if out['verify'].ok else 'fail'} ({out['verify'].summary})")
        print("output:")
        print(out['result'].output)

    if args.cmd == "doctor":
        overall, checks = run_doctor()
        print(f"overall: {'pass' if overall else 'fail'}")
        for name, ok, msg in checks:
            print(f"- {name}: {'pass' if ok else 'fail'} :: {msg}")


if __name__ == "__main__":
    main()
