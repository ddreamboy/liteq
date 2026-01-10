import argparse
import os
import sys

from .db import init_db
from .worker import Worker


def main():
    parser = argparse.ArgumentParser(description="LiteQ CLI")
    subparsers = parser.add_subparsers(dest="command")

    worker_parser = subparsers.add_parser("worker")
    worker_parser.add_argument("--app", required=True, help="Module with tasks (e.g. tasks.py)")
    worker_parser.add_argument("--queues", default="default", help="Comma separated queues")
    worker_parser.add_argument("--concurrency", type=int, default=4)

    monitor_parser = subparsers.add_parser("monitor")
    monitor_parser.add_argument("--port", type=int, default=5151)

    args = parser.parse_args()

    if args.command == "worker":
        sys.path.append(os.getcwd())
        module_name = args.app.replace(".py", "")
        __import__(module_name)

        init_db()
        Worker(queues=args.queues.split(","), concurrency=args.concurrency).run()

    elif args.command == "monitor":
        from .web import run_monitor

        run_monitor(port=args.port)


if __name__ == "__main__":
    main()
