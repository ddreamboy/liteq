from inspect import iscoroutinefunction
from functools import wraps

from liteq.registry import register_task


def task(name: str | None = None, max_retries: int = 3, queue: str = "default"):
    """
    Decorator to register a task function

    Args:
        name: Task name (defaults to function name)
        max_retries: Maximum number of retry attempts
        queue: Queue name for this task

    Example:
        @task(max_retries=3, queue='emails')
        async def send_email(to: str, subject: str):
            ...
    """

    def decorator(f):
        task_name = name or f.__name__

        register_task(task_name, f)

        if iscoroutinefunction(f):

            @wraps(f)
            async def async_wrapper(*args, **kwargs):
                return await f(*args, **kwargs)

            async_wrapper._task_name = task_name
            async_wrapper._max_retries = max_retries
            async_wrapper._queue = queue
            return async_wrapper
        else:

            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)

            wrapper._task_name = task_name
            wrapper._max_retries = max_retries
            wrapper._queue = queue
            return wrapper

    return decorator
