import functools
import json

from .db import get_conn

TASK_REGISTRY = {}


class TaskProxy:
    def __init__(self, fn, name, queue, max_retries, timeout):
        self.fn = fn
        self.name = name or fn.__name__
        self.queue = queue
        self.max_retries = max_retries
        self.timeout = timeout
        TASK_REGISTRY[self.name] = fn

    def delay(self, *args, **kwargs):
        """
        Enqueue task for background execution.

        Returns:
            int: Task ID

        Example:
            task_id = my_task.delay(arg1, arg2, kwarg1=val1)
        """
        payload = json.dumps({"args": args, "kwargs": kwargs})
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (name, payload, queue, max_retries, timeout) VALUES (?, ?, ?, ?, ?)",
                (self.name, payload, self.queue, self.max_retries, self.timeout),
            )
            return cursor.lastrowid

    def schedule(self, run_at, *args, **kwargs):
        """
        Schedule task to run at specific time.

        Args:
            run_at: datetime or ISO string

        Returns:
            int: Task ID

        Example:
            from datetime import datetime, timedelta
            task_id = my_task.schedule(datetime.now() + timedelta(hours=1), arg1, arg2)
        """
        from datetime import datetime

        if isinstance(run_at, datetime):
            run_at = run_at.isoformat()

        payload = json.dumps({"args": args, "kwargs": kwargs})
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (name, payload, queue, max_retries, timeout, run_at) VALUES (?, ?, ?, ?, ?, ?)",
                (self.name, payload, self.queue, self.max_retries, self.timeout, run_at),
            )
            return cursor.lastrowid

    def __call__(self, *args, **kwargs):
        """Execute task synchronously (for testing)"""
        return self.fn(*args, **kwargs)


def task(queue="default", max_retries=3, name=None, timeout=None):
    """
    Decorator to mark a function as a background task.

    Args:
        queue: Queue name (default: "default")
        max_retries: Maximum retry attempts (default: 3)
        name: Custom task name (default: function name)
        timeout: Task timeout in seconds (default: None)

    Example:
        @task(queue="emails", timeout=60)
        def send_email(to: str, subject: str):
            # ... send email
            pass

        # Enqueue for background execution
        task_id = send_email.delay("user@example.com", "Hello")

        # Schedule for later
        send_email.schedule(datetime.now() + timedelta(hours=1), "user@example.com", "Reminder")
    """

    def decorator(fn):
        proxy = TaskProxy(fn, name, queue, max_retries, timeout)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        wrapper.delay = proxy.delay
        wrapper.schedule = proxy.schedule
        wrapper._task_proxy = proxy
        return wrapper

    return decorator
