# LiteQ Development Guide

## Project Structure

```
liteq/
├── liteq/                  # Main package
│   ├── __init__.py        # Package exports
│   ├── db.py              # Database layer
│   ├── decorators.py      # @task decorator
│   ├── worker.py          # Worker implementation
│   ├── manager.py         # QueueManager
│   ├── producer.py        # Task enqueueing
│   ├── monitoring.py      # Stats and monitoring
│   ├── recovery.py        # Recovery functions
│   ├── registry.py        # Task registry
│   └── signals.py         # Signal handling
├── examples/              # Usage examples
│   ├── basic.py
│   ├── multiple_queues.py
│   ├── priorities.py
│   ├── monitoring.py
│   └── email_campaign.py
├── tests/                 # Unit tests
│   └── test_basic.py
├── README.md              # Main documentation
├── LICENSE                # MIT License
├── pyproject.toml         # Package metadata
├── setup.py               # Setup script
├── MANIFEST.in            # Package manifest
└── PUBLISH.md             # Publishing instructions
```

## Local Development

### Install in development mode

```bash
# From the project root
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

### Run tests

```bash
pytest
pytest -v
pytest --cov=liteq
```

### Run examples

```bash
python examples/basic.py
python examples/multiple_queues.py
python examples/email_campaign.py
```

## Key Features Implemented

### Named Queues
```python
@task(queue='emails')
async def send_email(to: str):
    pass

manager.add_worker("worker-1", queues=['emails', 'notifications'])
```

### QueueManager
```python
manager = QueueManager(db_path='myapp.db')
manager.initialize()
manager.add_worker("worker-1", queues=['default'])
await manager.start()
```

### Priority Tasks
```python
enqueue("urgent_task", {...}, priority=100)  # High priority
enqueue("normal_task", {...}, priority=10)
```

### Async & Sync Support
```python
@task()
async def async_task():
    await asyncio.sleep(1)

@task()
def sync_task():
    time.sleep(1)  # Both works!
```

### Monitoring
```python
from liteq import get_queue_stats, get_failed_tasks, retry_task

stats = get_queue_stats(queue='emails')
failed = get_failed_tasks(limit=10)
retry_task(task_id=123)
```

### Graceful Shutdown
- Signal handlers (SIGTERM, SIGINT)
- Workers stop cleanly
- Running tasks are paused
- Can be recovered on restart

## Usage Examples

### Simple Usage
```python
from liteq import task, QueueManager, enqueue

@task()
async def my_task(x: int):
    print(f"Processing {x}")

manager = QueueManager()
manager.initialize()
manager.add_worker("w1")

enqueue("my_task", {"x": 42})
await manager.start()
```

### Multiple Queues
```python
manager = QueueManager()
manager.initialize()

# Worker for emails only
manager.add_worker("email-worker", queues=['emails'])

# Worker for reports only  
manager.add_worker("report-worker", queues=['reports'])

# Worker for both
manager.add_worker("multi-worker", queues=['emails', 'reports'])

enqueue("send_email", {...}, queue='emails')
enqueue("generate_report", {...}, queue='reports')
```

## Publishing to PyPI

See [PUBLISH.md](PUBLISH.md) for detailed instructions.

Quick version:
```bash
# Build
python -m build

# Test on TestPyPI
python -m twine upload --repository testpypi dist/*

# Publish to PyPI
python -m twine upload dist/*
```

## Version History

- **0.1.0** - Initial release
  - Zero dependencies
  - Named queues
  - QueueManager
  - Priority tasks
  - Async/sync support
  - Monitoring tools
  - Graceful shutdown

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

- GitHub Issues: https://github.com/ddreamboy/liteq/issues
