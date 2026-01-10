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
📊 **Monitoring** - Track stats, workers, and task status  
💾 **Persistent** - SQLite-backed for reliability  
🚀 **Production Ready** - 92% test coverage  

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

### 3. Run worker

```bash
# Start a worker to process tasks
liteq worker --app tasks.py --queues default,reports --concurrency 4
```

That's it! Your tasks will be processed in the background.

## Examples

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

# Monitor dashboard (requires liteq[web])
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

### Decorators


#### `@task(queue='default', max_retries=3, name=None)`

Decorate a function to make it a task.

**Arguments:**
- `queue` (str): Queue name (default: "default")
- `max_retries` (int): Maximum retry attempts (default: 3)
- `name` (str, optional): Custom task name (defaults to function name)

**Returns:** A callable with a `.delay(*args, **kwargs)` method

**Example:**
```python
@task(queue="emails", max_retries=5)
def send_email(to: str):
    ...

# Enqueue task
task_id = send_email.delay(to="user@example.com")
```

### Worker

#### `Worker(queues, concurrency)`

Create a worker to process tasks.

**Arguments:**
- `queues` (list[str]): List of queue names to process
- `concurrency` (int): Number of concurrent processes

**Methods:**
- `run()`: Start processing tasks (blocks)

**Example:**
```python
from liteq.worker import Worker

worker = Worker(queues=["default", "emails"], concurrency=4)
worker.run()
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

### Database

#### `init_db()`

Initialize the database schema. Called automatically by CLI.

**Example:**
```python
from liteq.db import init_db

init_db() (@task)
│   ├── core.py           # Task decorator and registry
│   ├── db.py             # Database layer (SQLite)
│   ├── worker.py         # Worker implementation
│   ├── cli.py            # Command-line interface
│   ├── monitoring.py     # Stats and monitoring
│   └── web.py            # Web dashboard (optional)
├── examples/             # Complete examples
├── tests/                # 92% coverage
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