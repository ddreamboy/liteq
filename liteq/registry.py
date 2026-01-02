TASK_REGISTRY = {}


def register_task(name, func):
    """Register a task function"""
    TASK_REGISTRY[name] = func


def get_task(name):
    """Get a registered task function"""
    return TASK_REGISTRY.get(name)


def list_tasks():
    """List all registered tasks"""
    return list(TASK_REGISTRY.keys())
