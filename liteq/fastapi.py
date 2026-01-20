"""FastAPI integration for LiteQ"""

from typing import Callable

from .core import TaskProxy


class LiteQBackgroundTasks:
    """
    FastAPI-like background tasks that use LiteQ instead of in-process execution.

    Usage in FastAPI:
        from liteq.fastapi import LiteQBackgroundTasks

        @app.post("/send-email")
        async def send_email(background: LiteQBackgroundTasks):
            background.add_task(send_email_task, "user@example.com")
            return {"message": "Email queued"}
    """

    def __init__(self, queue: str = "default", priority: int = 0):
        self.queue = queue
        self.priority = priority
        self.tasks = []

    def add_task(self, func: Callable, *args, **kwargs):
        """Add task to queue (supports both regular functions and TaskProxy)"""
        if isinstance(func, TaskProxy):
            # It's already a task, use its delay method
            task_id = func.delay(*args, **kwargs)
        elif hasattr(func, "delay"):
            # It's a wrapped task
            task_id = func.delay(*args, **kwargs)
        else:
            raise ValueError(f"Function {func.__name__} is not a LiteQ task. Wrap it with @task decorator first.")
        self.tasks.append(task_id)
        return task_id


def enqueue_task(task_func: Callable, *args, **kwargs) -> int:
    """
    Convenience function to enqueue a task from FastAPI.

    Usage:
        from liteq.fastapi import enqueue_task

        @app.post("/process")
        async def process_data(data: dict):
            task_id = enqueue_task(process_data_task, data)
            return {"task_id": task_id}
    """
    if hasattr(task_func, "delay"):
        return task_func.delay(*args, **kwargs)
    else:
        raise ValueError(f"Function {task_func.__name__} is not a LiteQ task. Use @task decorator.")
