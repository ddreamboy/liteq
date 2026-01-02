from inspect import iscoroutinefunction
from functools import wraps

from registry import register_task

def task(name: str | None = None, max_retries: int = 3):
    def decorator(f):
        task_name = name or f.__name__
        
        register_task(task_name, f)
        
        if iscoroutinefunction(f):
            @wraps(f)
            async def async_wrapper(*args, **kwargs):
                return await f(*args, **kwargs)
            
            async_wrapper._task_name = task_name
            async_wrapper._max_retries = max_retries
            return async_wrapper
        else:
            @wraps(f)
            def wrapper(*args, **kwargs):
                return f(*args, **kwargs)
            
            wrapper._task_name = task_name
            wrapper._max_retries = max_retries
            return wrapper
    
    return decorator