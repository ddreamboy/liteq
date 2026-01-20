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

A lightweight, minimalist task queue for Python with **zero dependencies**.

LiteQ is a pure Python task queue built on SQLite, perfect for background job processing without the complexity of Celery or Redis. Just decorate your functions and call `.delay()` - that's it!

## Features

✨ **Zero Dependencies** - Pure Python 3.10+ with only SQLite  
⚡ **Dead Simple API** - Just `@task` decorator and `.delay()`  
🔄 **Async & Sync** - Works with both async and regular functions  
📦 **Multiple Queues** - Organize tasks by queue name  
🎯 **Task Priorities** - Control execution order  
🔁 **Auto Retry** - Configurable retry logic  
👷 **Multiple Workers** - Process tasks in parallel  
⏰ **Task Scheduling** - Cron-like scheduled tasks  
⏱️ **Task Timeouts** - Automatic timeout and stuck task handling  
🚀 **FastAPI Integration** - Built-in FastAPI support  
📊 **Monitoring** - Track stats, workers, and task status  
💾 **Persistent** - SQLite-backed for reliability  
🧪 **Production Ready** - test coverage >80%

## Installation

```bash
pip install liteq
```

## Quick Start

### 1. Define your tasks

Create a file `tasks.py`:

```python
from liteq import task
import time

@task()
def send_email(to: str, subject: str):
    print(f"Sending email to {to}: {subject}")
    time.sleep(1)
    return f"Email sent to {to}"

@task(queue="reports", max_retries=5)
def generate_report(report_id: int):
    print(f"Generating report {report_id}")
    time.sleep(2)
    return {"report_id": report_id, "status": "completed"}
```

### 2. Enqueue tasks

```python
from tasks import send_email, generate_report

# Enqueue tasks - they return task IDs
task_id = send_email.delay(to="user@example.com", subject="Hello!")
print(f"Enqueued task: {task_id}")

# Enqueue to different queue
report_id = generate_report.delay(report_id=123)
```

### 3. Check task status

```python
from liteq import get_task_status

# Get task status
status = get_task_status(task_id)
if status:
    print(f"Status: {status['status']}")  # pending/running/done/failed
    print(f"Attempts: {status['attempts']}/{status['max_retries']}")
    
    if status['status'] == 'done':
        print(f"Result: {status['result']}")
    elif status['status'] == 'failed':
        print(f"Error: {status['error']}")
```

### 4. Run worker

```bash
# Start a worker to process tasks
liteq worker --app tasks.py --queues default,reports --concurrency 4
```

That's it! Your tasks will be processed in the background.

## Examples

### FastAPI Integration

```python
from fastapi import FastAPI
from liteq import task, get_task_status
from liteq.fastapi import LiteQBackgroundTasks, enqueue_task

app = FastAPI()

@task(queue="emails", timeout=60)
async def send_email(to: str, subject: str):
    # Send email logic
    return {"sent": True}

# Method 1: Simple .delay()
@app.post("/send-email")
async def api_send_email(to: str, subject: str):
    task_id = send_email.delay(to, subject)
    return {"task_id": task_id}

# Method 2: FastAPI-like BackgroundTasks with status checking
@app.post("/send-email-bg")
async def api_send_email_bg(to: str, background: LiteQBackgroundTasks):
    task_id = background.add_task(send_email, to, "Hello!")
    return {"message": "queued", "task_id": task_id}

# Method 3: Helper function
@app.post("/send-email-helper")
async def api_send_email_helper(to: str):
    task_id = enqueue_task(send_email, to, "Welcome")
    return {"task_id": task_id}

# Check task status
@app.get("/tasks/{task_id}")
async def check_task_status(task_id: int):
    status = get_task_status(task_id)
    if not status:
        return {"error": "Task not found"}, 404
    return {
        "task_id": status["id"],
        "status": status["status"],
        "result": status.get("result"),
        "error": status.get("error")
    }
```

### Scheduled Tasks (Cron)

```python
from liteq import task, register_schedule
from liteq.scheduler import Scheduler

@task()
def daily_backup():
    print("Running backup...")
    return {"status": "success"}

@task()
def cleanup():
    print("Cleaning up...")

# Register schedules
register_schedule(daily_backup, "0 2 * * *")  # Every day at 2 AM
register_schedule(cleanup, "*/5 * * * *")  # Every 5 minutes

# Run scheduler
scheduler = Scheduler(check_interval=60)
scheduler.run()
```

```bash
# Or via CLI
liteq scheduler --app tasks.py --interval 60
```

### Task Timeouts

```python
from liteq import task

# Timeout on task level
@task(timeout=30)  # 30 seconds
def slow_task():
    import time
    time.sleep(100)  # Will be killed after 30s

# Timeout on worker level
# liteq worker --app tasks.py --timeout 60
```

### Delayed Execution

```python
from liteq import task
from datetime import datetime, timedelta

@task()
def reminder(message: str):
    print(f"Reminder: {message}")

# Schedule for later
run_time = datetime.now() + timedelta(hours=1)
task_id = reminder.schedule(run_time, "Meeting in 1 hour")
```

### Async Tasks

```python
import asyncio
from liteq import task

@task()
async def fetch_data(url: str):
    print(f"Fetching {url}")
    await asyncio.sleep(1)
    return {"url": url, "data": "..."}

# Enqueue
task_id = fetch_data.delay(url="https://api.example.com")
```

### Multiple Queues

```python
from liteq import task

@task(queue="emails")
def send_email(to: str):
    print(f"Email to {to}")

@task(queue="reports")
def generate_report(id: int):
    print(f"Report {id}")

@task(queue="notifications")
def send_push(user_id: int, message: str):
    print(f"Push to {user_id}: {message}")

# Enqueue to different queues
send_email.delay(to="user@example.com")
generate_report.delay(id=42)
send_push.delay(user_id=1, message="Hello!")
```

### Task Priorities

```python
from liteq import task

@task()
def process_item(item_id: int):
    return f"Processed {item_id}"

# Higher priority number = runs first
# These are enqueued to the same queue but with different priorities
# (Note: priority is set in the task definition or database, 
# not in .delay() call in current version)
```

### Custom Task Names and Retries

```python
from liteq import task

@task(name="custom_email_task", max_retries=5)
def send_email(to: str):
    # This task will retry up to 5 times on failure
    print(f"Sending to {to}")

@task(max_retries=0)  # No retries
def one_time_task():
    print("This runs only once")
```

### CLI Usage

```bash
# Run worker
liteq worker --app tasks.py

# Multiple queues
liteq worker --app tasks.py --queues emails,reports,notifications

# Custom concurrency
liteq worker --app tasks.py --concurrency 8

# With timeout (kills stuck tasks)
liteq worker --app tasks.py --timeout 300

# Run scheduler
liteq scheduler --app tasks.py --interval 60

# Monitor dashboard
liteq monitor --port 5151
```

### Programmatic Worker

```python
from liteq.db import init_db
from liteq.worker import Worker

# Initialize database
init_db()

# Create and run worker
worker = Worker(queues=["default", "emails"], concurrency=4)
worker.run()  # This blocks
```

### Monitoring

```python
from liteq.monitoring import (
    get_queue_stats,
    get_recent_tasks,
    list_queues,
    get_failed_tasks,
    get_active_workers,
)

# Get queue statistics
stats = get_queue_stats()
for stat in stats:
    print(f"{stat['queue']}: {stat['count']} tasks ({stat['status']})")

# List all queues
queues = list_queues()
print(f"Queues: {queues}")

# Get recent tasks
recent = get_recent_tasks(limit=10)

# Get failed tasks
failed = get_failed_tasks(limit=5)
for task in failed:
    print(f"Task {task['id']} failed: {task['error']}")

# Get active workers
workers = get_active_workers()
for worker in workers:
    print(f"Worker {worker['worker_id']}: {worker['active_tasks']} active tasks")
```

## More Examples

Check out the [examples/](examples/) directory for complete working examples:

- **[basic.py](examples/basic.py)** - Simple introduction with async and sync tasks
- **[multiple_queues.py](examples/multiple_queues.py)** - Multiple queues with different workers
- **[priorities.py](examples/priorities.py)** - Task priority demonstration
- **[monitoring.py](examples/monitoring.py)** - Queue monitoring and statistics
- **[email_campaign.py](examples/email_campaign.py)** - Real-world email campaign example

Run any example:
```bash
python examples/basic.py
```

## API Reference

### Core Functions

#### `get_task_status(task_id: int) -> dict | None`

Get task status and details by task ID.

**Arguments:**
- `task_id` (int): Task ID returned by `.delay()` or `.schedule()`

**Returns:** Dictionary with task information or `None` if not found

**Example:**
```python
from liteq import task, get_task_status

@task()
def process_data(x: int):
    return x * 2

task_id = process_data.delay(5)

# Check status
status = get_task_status(task_id)
if status:
    print(f"Status: {status['status']}")  # pending/running/done/failed
    print(f"Attempts: {status['attempts']}/{status['max_retries']}")
    if status['status'] == 'done':
        print(f"Result: {status['result']}")
```

### Decorators


#### `@task(queue='default', max_retries=3, name=None, timeout=None)`

Decorate a function to make it a task.

**Arguments:**
- `queue` (str): Queue name (default: "default")
- `max_retries` (int): Maximum retry attempts (default: 3)
- `name` (str, optional): Custom task name (defaults to function name)
- `timeout` (int, optional): Task timeout in seconds (default: None)

**Returns:** A callable with `.delay(*args, **kwargs)` and `.schedule(run_at, *args, **kwargs)` methods

**Example:**
```python
@task(queue="emails", max_retries=5, timeout=60)
def send_email(to: str):
    ...

# Enqueue task
task_id = send_email.delay(to="user@example.com")

# Schedule for later
from datetime import datetime, timedelta
run_time = datetime.now() + timedelta(hours=1)
task_id = send_email.schedule(run_time, to="user@example.com")
```

### Worker

#### `Worker(queues, concurrency, task_timeout=None)`

Create a worker to process tasks.

**Arguments:**
- `queues` (list[str]): List of queue names to process
- `concurrency` (int): Number of concurrent threads
- `task_timeout` (int, optional): Timeout in seconds for stuck tasks (default: None)

**Methods:**
- `run()`: Start processing tasks (blocks)

**Example:**
```python
from liteq.worker import Worker

# Basic worker
worker = Worker(queues=["default", "emails"], concurrency=4)
worker.run()

# Worker with timeout
worker = Worker(queues=["default"], concurrency=4, task_timeout=300)
worker.run()  # Kills tasks running longer than 5 minutes
```

### Monitoring Functions

All available in `liteq.monitoring`:

#### `get_queue_stats() -> list[dict]`

Get statistics grouped by queue and status.

#### `get_recent_tasks(limit=50) -> list[dict]`

Get recent tasks ordered by creation time.

#### `list_queues() -> list[str]`

Get list of all unique queue names.

#### `get_failed_tasks(limit=50) -> list[dict]`

Get recent failed tasks.

#### `get_active_workers() -> list[dict]`

Get currently active workers (heartbeat < 15 seconds ago).

### Scheduler Functions

All available in `liteq.scheduler`:

#### `register_schedule(task_func, cron_expr, queue='default', **kwargs) -> int`

Register a task to run on a schedule.

**Example:**
```python
from liteq import task, register_schedule

@task()
def backup():
    print("Backup running")

# Every day at 2 AM
schedule_id = register_schedule(backup, "0 2 * * *")

# Every 5 minutes
schedule_id = register_schedule(backup, "*/5 * * * *")
```

#### `Scheduler(check_interval=60)`

Scheduler daemon that processes scheduled tasks.

**Example:**
```python
from liteq.scheduler import Scheduler

scheduler = Scheduler(check_interval=60)
scheduler.run()  # Blocks
```

### FastAPI Integration

All available in `liteq.fastapi`:

#### `LiteQBackgroundTasks`

FastAPI-like background tasks using LiteQ.

**Methods:**
- `add_task(func, *args, **kwargs) -> int` - Add task and return task ID
- `get_task_status(task_id: int) -> dict | None` - Get status of specific task
- `get_all_statuses() -> list[dict]` - Get statuses of all tasks in this background instance
- `task_ids` (property) - List of all task IDs

**Example:**
```python
from fastapi import FastAPI
from liteq.fastapi import LiteQBackgroundTasks
from liteq import task

app = FastAPI()

@task()
def send_email_task(to: str):
    # Send email
    return {"sent": True}

@app.post("/send-email")
async def send_email(to: str, background: LiteQBackgroundTasks):
    task_id = background.add_task(send_email_task, to)
    return {"message": "queued", "task_id": task_id}

@app.post("/batch-emails")
async def batch_emails(recipients: list[str], background: LiteQBackgroundTasks):
    for recipient in recipients:
        background.add_task(send_email_task, recipient)
    
    return {
        "message": f"Queued {len(recipients)} emails",
        "task_ids": background.task_ids
    }

@app.get("/batch-status")
async def batch_status(background: LiteQBackgroundTasks):
    statuses = background.get_all_statuses()
    return {"tasks": statuses}
```

#### `enqueue_task(task_func, *args, **kwargs) -> int`

Helper to enqueue a task.

### Database

#### `init_db()`

Initialize the database schema. Called automatically by CLI.

**Example:**
```python
from liteq.db import init_db

init_db()
│   ├── core.py           # Task decorator and registry
│   ├── db.py             # Database layer (SQLite)
│   ├── worker.py         # Worker implementation
│   ├── cli.py            # Command-line interface
│   ├── monitoring.py     # Stats and monitoring
│   └── web.py            # Web dashboard (optional)
├── examples/             # Complete examples
├── tests/                # >80% coverage
├── README.md
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
- Environment Variables

- `LITEQ_DB` - Database file path (default: `liteq.db`)

```bash
export LITEQ_DB=/path/to/tasks.db
liteq worker --app tasks.py
```

## Database Schema

LiteQ uses a simple SQLite database with two tables:

**tasks:**
- `id` - Primary key
- `name` - Task function name
- `payload` - JSON args/kwargs
- `queue` - Queue name
- `status` - pending/running/done/failed
- `priority` - Integer (higher = first)
- `attempts` - Current attempt count
- `max_retries` - Max retry limit
- `worker_id` - Processing worker
- `run_at` - Scheduled run time
- `created_at` - Creation timestamp
- `finished_at` - Completion timestamp
- `result` - JSON result
- `error` - Error message

**workers:**
- `worker_id` - Primary key
- `hostname` - Worker hostname
- `queues` - Comma-separated queues
- `concurrency` - Process count
- `last_heartbeat` - Last ping time

## Use Cases

- 📧 Email sending queues
- 📊 Report generation  
- 🖼️ Image/video processing
- 📱 Push notifications
- 🧹 Cleanup/maintenance tasks
- 📈 Analytics pipelines
- 🔄 Webhook delivery
- 📦 Batch operations
- 🔍 Web scraping
- 💾 Data imports

## Why LiteQ?

**Simple** - Minimal API, zero configuration  
**Lightweight** - No dependencies, small codebase  
**Fast** - SQLite is surprisingly performant  
**Reliable** - WAL mode, ACID transactions  
**Debuggable** - It's just SQLite, inspect with any SQL tool  
**Pythonic** - Feels natural, not enterprise-y

## When NOT to use LiteQ

- Millions of tasks per second
- Distributed/multi-node setups
- Network filesystems (NFS, SMB)
- Tasks larger than a few MB
- Real-time streaming

For these, use RabbitMQ, Redis, Kafka, or cloud service

## Contributing

Contributions welcome! Please feel free to submit a Pull Request.

## Links

- [PyPI](https://pypi.org/project/liteq/)
- [GitHub](https://github.com/ddreamboy/liteq)
- [Documentation](https://github.com/ddreamboy/liteq#readme)