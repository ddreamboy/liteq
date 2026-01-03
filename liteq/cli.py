import argparse
import sys


def main():
    parser = argparse.ArgumentParser(
        description="LiteQ - Lightweight task queue system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  liteq monitor                    # Start web monitoring UI
  liteq monitor --port 8080        # Start on custom port
  liteq monitor --db tasks.db      # Use specific database
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Start web monitoring UI")
    monitor_parser.add_argument(
        "--db",
        default="tasks.db",
        help="Path to SQLite database (default: tasks.db)",
    )
    monitor_parser.add_argument(
        "--host", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)"
    )
    monitor_parser.add_argument(
        "--port", type=int, default=5151, help="Port to bind to (default: 5151)"
    )

    args = parser.parse_args()

    if args.command == "monitor":
        from liteq.web import run_monitor

        run_monitor(db_path=args.db, host=args.host, port=args.port)
    elif args.command is None:
        parser.print_help()
        sys.exit(1)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
