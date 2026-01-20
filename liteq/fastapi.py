"""FastAPI integration for LiteQ"""

from typing import Callable, List, Optional

from .core import TaskProxy, get_task_status


class LiteQBackgroundTasks:
    """
    FastAPI-like background tasks that use LiteQ instead of in-process execution.

    Usage in FastAPI:
        from liteq.fastapi import LiteQBackgroundTasks

        @app.post("/send-email")
        async def send_email(background: LiteQBackgroundTasks):
            task_id = background.add_task(send_email_task, "user@example.com")
            return {"message": "Email queued", "task_id": task_id}
    """

    def __init__(self, queue: str = "default", priority: int = 0):
        self.queue = queue
        self.priority = priority
        self.tasks = []

    def add_task(self, func: Callable, *args, **kwargs) -> int:
        """
        Add task to queue and return task ID.

        Args:
            func: Task function decorated with @task
            *args: Positional arguments for task
            **kwargs: Keyword arguments for task

        Returns:
            int: Task ID that can be used to check status

        Example:
            task_id = background.add_task(send_email, "user@example.com")
            status = background.get_task_status(task_id)
        """
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

    def get_task_status(self, task_id: int) -> Optional[dict]:
        """
        Get status of a specific task.

        Args:
            task_id: Task ID returned by add_task()

        Returns:
            dict: Task information or None if not found

        Example:
            status = background.get_task_status(task_id)
            if status and status['status'] == 'done':
                print(f"Result: {status['result']}")
        """
        return get_task_status(task_id)

    def get_all_statuses(self) -> List[dict]:
        """
        Get statuses of all tasks added to this background instance.

        Returns:
            list: List of task status dicts

        Example:
            statuses = background.get_all_statuses()
            for status in statuses:
                print(f"Task {status['id']}: {status['status']}")
        """
        return [get_task_status(tid) for tid in self.tasks if get_task_status(tid)]

    @property
    def task_ids(self) -> List[int]:
        """Get list of all task IDs added to this background instance"""
        return self.tasks.copy()


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
