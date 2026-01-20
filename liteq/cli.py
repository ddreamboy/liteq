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
    worker_parser.add_argument("--timeout", type=int, default=None, help="Task timeout in seconds (kills stuck tasks)")

    monitor_parser = subparsers.add_parser("monitor")
    monitor_parser.add_argument("--port", type=int, default=5151)

    scheduler_parser = subparsers.add_parser("scheduler")
    scheduler_parser.add_argument("--app", required=True, help="Module with scheduled tasks")
    scheduler_parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")

    args = parser.parse_args()

    if args.command == "worker":
        sys.path.append(os.getcwd())
        module_name = args.app.replace(".py", "")
        __import__(module_name)

        init_db()
        Worker(queues=args.queues.split(","), concurrency=args.concurrency, task_timeout=args.timeout).run()

    elif args.command == "monitor":
        from .web import run_monitor

        run_monitor(port=args.port)

    elif args.command == "scheduler":
        sys.path.append(os.getcwd())
        module_name = args.app.replace(".py", "")
        __import__(module_name)

        init_db()
        from .scheduler import Scheduler

        Scheduler(check_interval=args.interval).run()


if __name__ == "__main__":
    main()
