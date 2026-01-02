TASK_REGISTRY = {}

def register_task(name, func):
    TASK_REGISTRY[name] = func

def get_task(name):
    return TASK_REGISTRY.get(name)