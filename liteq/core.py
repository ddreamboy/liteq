import functools
import json

from .db import get_conn

TASK_REGISTRY = {}


class TaskProxy:
    def __init__(self, fn, name, queue, max_retries):
        self.fn = fn
        self.name = name or fn.__name__
        self.queue = queue
        self.max_retries = max_retries
        TASK_REGISTRY[self.name] = fn

    def delay(self, *args, **kwargs):
        payload = json.dumps({"args": args, "kwargs": kwargs})
        with get_conn() as conn:
            cursor = conn.execute(
                "INSERT INTO tasks (name, payload, queue, max_retries) VALUES (?, ?, ?, ?)",
                (self.name, payload, self.queue, self.max_retries),
            )
            return cursor.lastrowid


def task(queue="default", max_retries=3, name=None):
    def decorator(fn):
        proxy = TaskProxy(fn, name, queue, max_retries)

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)

        wrapper.delay = proxy.delay
        return wrapper

    return decorator
