# LiteQ

<p align="center">
  <a href="https://github.com/ddreamboy/liteq/actions/workflows/tests.yml"><img src="https://github.com/ddreamboy/liteq/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://codecov.io/gh/ddreamboy/liteq"><img src="https://codecov.io/gh/ddreamboy/liteq/branch/master/graph/badge.svg" alt="codecov"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.10%2B-blue.svg" alt="Python Version"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

<p align="center">
  <b>Translations:</b> <a href="docs/README_ru.md">🇷🇺 Русский</a>
</p>

A lightweight, fast, and simple message queue for Python with **zero dependencies**.

LiteQ is a pure Python message queue system built on SQLite, perfect for background task processing, job queues, and async workflows without the complexity of Redis, RabbitMQ, or Celery!

## Features

**Zero Dependencies** - Pure Python 3.10+ with only SQLite  
**Async/Sync Support** - Works with both async and sync task functions  
**Multiple Queues** - Organize tasks into named queues  
**Priority Tasks** - Higher priority tasks run first  
**Auto Retry** - Exponential backoff for failed tasks  
**Multiple Workers** - Scale horizontally with multiple workers  
**Long-Running Tasks** - Progress tracking, checkpoints, and cancellation support  
**Monitoring** - Built-in queue statistics and task tracking  
**Graceful Shutdown** - Signal handling for clean shutdowns  
**Persistent** - SQLite-backed for reliability  

## Installation

```bash
pip install liteq
```

## Quick Start

### Simple Example

```python
import asyncio
from liteq import task, QueueManager

# Define a task
@task(max_retries=3, queue='emails')
async def send_email(to: str, subject: str):
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(1)

# Initialize and run
async def main():
    manager = QueueManager()
    manager.initialize()
    
    # Add a worker for the 'emails' queue
    manager.add_worker("worker-1", queues=['emails'])
    
    # Enqueue some tasks
    from liteq import enqueue
    enqueue("send_email", {"to": "user@example.com", "subject": "Hello!"}, queue='emails')
    
    # Start processing
    await manager.start()

asyncio.run(main())
```

### Multiple Queues Example

```python
import asyncio
from liteq import task, QueueManager, enqueue

@task(queue='emails', max_retries=3)
async def send_email(to: str, subject: str):
    print(f"Sending email to {to}: {subject}")
    await asyncio.sleep(1)

@task(queue='reports', max_retries=5)
async def generate_report(report_id: int):
    print(f"Generating report {report_id}")
    await asyncio.sleep(2)

@task(queue='notifications', max_retries=2)
def send_sms(phone: str, message: str):
    """Synchronous tasks work too!"""
    print(f"SMS to {phone}: {message}")
    import time
    time.sleep(0.5)

async def main():
    manager = QueueManager(db_path='myapp.db')
    manager.initialize()
    
    # Worker 1: handles emails and notifications
    manager.add_worker("worker-1", queues=['emails', 'notifications'])
    
    # Worker 2: dedicated to reports
    manager.add_worker("worker-2", queues=['reports'])
    
    # Worker 3: handles all queues
    manager.add_worker("worker-3", queues=['emails', 'reports', 'notifications'])
    
    # Enqueue tasks
    enqueue("send_email", {"to": "user@example.com", "subject": "Welcome!"}, queue='emails')
    enqueue("generate_report", {"report_id": 123}, queue='reports', priority=10)
    enqueue("send_sms", {"phone": "+1234567890", "message": "Hello!"}, queue='notifications')
    
    # Start all workers
    await manager.start()

asyncio.run(main())
```

### Batch Enqueue

```python
from liteq import enqueue_many

tasks = [
    {"task_name": "send_email", "payload": {"to": "user1@example.com", "subject": "Hi"}, "queue": "emails"},
    {"task_name": "send_email", "payload": {"to": "user2@example.com", "subject": "Hi"}, "queue": "emails"},
    {"task_name": "generate_report", "payload": {"report_id": 456}, "queue": "reports", "priority": 5},
]

task_ids = enqueue_many(tasks)
print(f"Enqueued {len(task_ids)} tasks")
```

### Task Priorities

```python
from liteq import enqueue

# Higher priority = runs first
enqueue("send_email", {"to": "vip@example.com", "subject": "Urgent"}, priority=100)
enqueue("send_email", {"to": "regular@example.com", "subject": "Normal"}, priority=10)
enqueue("send_email", {"to": "bulk@example.com", "subject": "Newsletter"}, priority=1)
```

### Delayed Tasks

```python
from liteq import enqueue

# Run after 60 seconds
enqueue("send_reminder", {"user_id": 123}, delay=60)

# Run after 1 hour
enqueue("cleanup_temp_files", {}, delay=3600)
```

### Monitoring

#### Web UI (like Flower) 🚀

LiteQ includes a beautiful web interface for monitoring workers and tasks in real-time:

```bash
# Install web dependencies
pip install liteq[web]

# Start the monitoring UI
liteq monitor

# Or with custom options
liteq monitor --host 0.0.0.0 --port 5151 --db tasks.db
```

Then open your browser to: **http://127.0.0.1:5151**

**Features:**
- 📊 Real-time statistics (tasks, workers, queues)
- 👷 Active worker monitoring with performance metrics
- 📋 Task management (view, cancel)
- 🔄 Auto-refresh every 5 seconds
- 📈 Queue analytics

For more details, see [Web Monitor Documentation](docs/WEB_MONITOR.md)

#### Programmatic Monitoring

```python
from liteq import get_queue_stats, get_failed_tasks, retry_task

# Get statistics
stats = get_queue_stats(queue='emails')
print(stats)
# [{'queue': 'emails', 'status': 'pending', 'count': 5, 'avg_attempts': 0}]

# Get failed tasks
failed = get_failed_tasks(limit=10, queue='emails')
for task in failed:
    print(f"Task {task['id']} failed: {task['last_error']}")
    
    # Retry a failed task
    retry_task(task['id'])

# Get pending count
from liteq import get_pending_count
pending = get_pending_count(queue='emails')
print(f"Pending tasks in emails queue: {pending}")
```

### Long-Running Tasks

```python
import asyncio
from liteq import task, QueueManager, enqueue, cancel_task

@task
async def process_large_dataset(ctx, dataset_size: int = 1000):
    """Long-running task with progress tracking and cancellation support"""
    
    # Load previous progress if task was paused/resumed
    progress = ctx.load_progress()
    start_from = progress.get("payload", {}).get("processed", 0) if progress else 0
    
    results = []
    for i in range(start_from, dataset_size):
        # Check for cancellation
        if ctx.cancelled:
            ctx.save_progress(f"cancelled_at_{i}", {"processed": i})
            return {"status": "cancelled", "processed": i}
        
        # Check for pause
        if ctx.paused:
            ctx.save_progress(f"paused_at_{i}", {"processed": i})
            return {"status": "paused", "processed": i}
        
        # Process item
        await asyncio.sleep(0.1)
        results.append(f"result_{i}")
        
        # Save checkpoint every 100 items
        if (i + 1) % 100 == 0:
            ctx.save_progress(f"step_{i + 1}", {"processed": i + 1})
    
    # Save final result
    ctx.save_result({"status": "completed", "total": len(results)})
    return {"status": "completed", "total": len(results)}

# Enqueue and manage long-running task
task_id = enqueue("process_large_dataset", {"dataset_size": 5000})

# Cancel if needed
cancel_task(task_id)
```

### Recovery & Cleanup

```python
from liteq import recover_stuck_tasks, cleanup_old_tasks

# Recover tasks stuck for more than 30 minutes
recovered = recover_stuck_tasks(timeout_minutes=30)

# Clean up completed/failed tasks older than 7 days
cleaned = cleanup_old_tasks(days=7, queue='emails')
```

## More Examples

Check out the [examples/](examples/) directory for complete working examples:

- **[basic.py](examples/basic.py)** - Simple introduction to LiteQ with async and sync tasks
- **[multiple_queues.py](examples/multiple_queues.py)** - Using multiple named queues with different workers
- **[priorities.py](examples/priorities.py)** - Task priority execution order demonstration
- **[long_running.py](examples/long_running.py)** - Long-running tasks with progress tracking, checkpoints, and cancellation
- **[monitoring.py](examples/monitoring.py)** - Queue monitoring, statistics, and task management
- **[email_campaign.py](examples/email_campaign.py)** - Real-world email campaign system

Run any example:
```bash
python examples/basic.py
```

## API Reference

### Decorators

#### `@task(name=None, max_retries=3, queue='default')`

Register a function as a task.

**Arguments:**
- `name` (str, optional): Task name (defaults to function name)
- `max_retries` (int): Maximum retry attempts
- `queue` (str): Queue name for this task

### QueueManager

Main manager for coordinating workers and queues.

#### `QueueManager(db_path='tasks.db')`

Create a new queue manager.

#### `manager.initialize()`

Initialize database and recover tasks.

#### `manager.add_worker(worker_id, queues=None, poll_interval=1)`

Add a worker.

**Arguments:**
- `worker_id` (str): Unique worker identifier
- `queues` (list): Queue names to process (default: `['default']`)
- `poll_interval` (int): Polling interval in seconds

#### `manager.start(setup_signal_handlers=True)`

Start all workers (async).

#### `manager.stop()`

Stop all workers gracefully (async).

### Functions

#### `enqueue(task_name, payload=None, delay=0, max_retries=3, priority=0, queue='default')`

Enqueue a single task.

#### `enqueue_many(tasks)`

Enqueue multiple tasks in one transaction.

#### `get_queue_stats(queue=None)`

Get queue statistics.

#### `get_task_by_id(task_id)`

Get task details.

#### `get_failed_tasks(limit=100, queue=None)`

Get recent failed tasks.

#### `retry_task(task_id)`

Retry a failed task.

#### `recover_stuck_tasks(timeout_minutes=30, queue=None)`

Recover stuck tasks.

#### `cleanup_old_tasks(days=30, queue=None)`

Delete old completed/failed tasks.

## Project Structure

```
liteq/
├── liteq/
│   ├── __init__.py       # Main exports
│   ├── db.py             # Database layer
│   ├── decorators.py     # @task decorator
│   ├── worker.py         # Worker implementation
│   ├── manager.py        # QueueManager
│   ├── producer.py       # Task enqueueing
│   ├── monitoring.py     # Stats and monitoring
│   ├── recovery.py       # Recovery functions
│   ├── registry.py       # Task registry
│   └── signals.py        # Signal handling
├── examples/
├── tests/
├── README.md
├── LICENSE
├── pyproject.toml
└── setup.py
```

## Development

### Setup

```bash
git clone https://github.com/ddreamboy/liteq.git
cd liteq
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

Or install only test dependencies:

```bash
pip install -r requirements-test.txt
```

### Run Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=liteq --cov-report=html

# Verbose output
pytest -v
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .
```

### Publish to PyPI

```bash
# Build
python -m build

# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# Upload to PyPI
python -m twine upload dist/*
```

## Use Cases

- 📧 Email sending queues
- 📊 Report generation
- 🖼️ Image processing
- 📱 Push notifications
- 🧹 Cleanup tasks
- 📈 Analytics processing
- 🔄 Webhook delivery
- 📦 Batch operations

## Why LiteQ?

- **Simple**: No external services to manage
- **Lightweight**: Zero dependencies beyond Python stdlib
- **Fast**: SQLite is surprisingly fast for most use cases
- **Reliable**: Persistent storage with WAL mode
- **Flexible**: Multiple queues, priorities, delays

## Limitations

- Not suitable for extremely high-throughput scenarios (millions of tasks/second)
- Single-node only (no distributed clustering)
- SQLite file locking limitations on network filesystems

For those use cases, consider RabbitMQ, Redis, or cloud-based solutions.

## License

MIT License - see [LICENSE](LICENSE) file.

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Links

- [PyPI](https://pypi.org/project/liteq/)
- [GitHub](https://github.com/ddreamboy/liteq)
- [Documentation](https://github.com/ddreamboy/liteq#readme)