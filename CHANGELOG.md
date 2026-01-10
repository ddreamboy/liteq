# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-01-10

### 🎉 Major Rewrite - Simplified API

This release represents a complete architectural simplification of LiteQ, focusing on minimalism and ease of use.

### Changed - BREAKING CHANGES
- **Removed `QueueManager`** - No longer needed, use CLI or direct Worker class instead
- **Removed `enqueue()` function** - Use `task.delay()` method instead
- **Removed `enqueue_many()` function** - Call `.delay()` multiple times or use database functions directly
- **Simplified task registration** - Tasks are now registered via `@task` decorator only
- **New execution model** - Use CLI `liteq worker` or programmatic `Worker.run()`

### Added
- **`@task` decorator** with `.delay()` method - Simple, Pythonic task enqueueing
- **CLI interface** - `liteq worker` command for running workers
- **Improved monitoring** - Enhanced monitoring functions in `liteq.monitoring`
- **Better documentation** - Complete rewrite of README and examples
- **92% test coverage** - Comprehensive test suite with pytest
- **Worker class** - Simplified `Worker(queues, concurrency)` for programmatic use
- **Database utilities** - Direct access via `liteq.db` module

### Fixed
- Cross-platform support in release script (Windows/Unix)
- Test isolation issues with shared database
- CLI worker import and execution
- Documentation accuracy

### Migration Guide from 0.1.x to 0.2.0

**Before (0.1.x):**
```python
from liteq import task, QueueManager, enqueue

@task(queue="emails")
async def send_email(to: str):
    ...

manager = QueueManager()
manager.initialize()
manager.add_worker("worker-1", queues=["emails"])

enqueue("send_email", {"to": "user@example.com"})
await manager.start()
```

**After (0.2.0):**
```python
from liteq import task
from liteq.db import init_db
from liteq.worker import Worker

@task(queue="emails")
async def send_email(to: str):
    ...

# Enqueue tasks
init_db()
send_email.delay(to="user@example.com")

# Run worker via CLI
# $ liteq worker --app tasks.py --queues emails

# Or programmatically
worker = Worker(queues=["emails"], concurrency=4)
worker.run()
```

## [0.1.3] - 2026-01-03

### Added
- **Web Monitoring UI** - Flower-like web interface for monitoring workers and tasks
  - Real-time dashboard with task statistics
  - Active worker monitoring with performance metrics
  - Task management (view, retry, cancel)
  - Auto-refresh every 5 seconds
  - Modern, responsive UI with multiple tabs
- New monitoring functions: `get_active_workers()`, `get_recent_tasks()`, `get_task_timeline()`, `get_worker_performance()`
- REST API endpoints for monitoring and task management
- CLI command `liteq monitor` for easy web UI startup
- FastAPI-based web server with Jinja2 templates
- Complete web monitoring documentation in `docs/WEB_MONITOR.md`
- Example scripts: `web_monitor.py` and `demo_monitor.py`
- Optional `[web]` installation extra for web dependencies

## [0.1.2] - 2026-01-03

### Fixed
- Worker stability improvements
- Manager lifecycle fixes

### Added
- GitHub Actions CI/CD workflow
- Code coverage reporting
- Automated testing on Python 3.10, 3.11, 3.12

## [0.1.1] - 2026-01-02

### Added
- **Long-running task support** - Major feature addition for handling tasks with extended execution times
- Watchdog process for monitoring long-running tasks
- Heartbeat mechanism to track task progress
- Automatic detection and recovery of stuck long-running tasks
- Context manager for long task execution with automatic cleanup

### Fixed
- Worker stability improvements
- Task recovery mechanism enhancements
- Documentation updates

## [0.1.0] - 2026-01-02

### Added
- Initial release of LiteQ
- Zero-dependency message queue built on SQLite
- Support for async and sync task functions
- Named queues for task organization
- `QueueManager` for coordinating multiple workers
- Worker support for multiple queue assignments
- Task priorities (higher priority runs first)
- Automatic retry with exponential backoff
- Delayed task execution
- Batch task enqueueing with `enqueue_many()`
- Queue monitoring and statistics
- Failed task tracking and retry capability
- Stuck task recovery
- Old task cleanup
- Graceful shutdown with signal handling
- WAL mode for better SQLite concurrency
- Comprehensive documentation and examples

### Features
- `@task()` decorator for registering tasks
- `QueueManager` class for managing workers
- `Worker` class with queue filtering
- `enqueue()` for single task enqueueing
- `enqueue_many()` for batch operations
- `get_queue_stats()` for monitoring
- `get_failed_tasks()` for error tracking
- `retry_task()` for manual retries
- `recover_stuck_tasks()` for recovery
- `cleanup_old_tasks()` for maintenance

### Documentation
- Comprehensive README with examples
- Quick start guide
- Development guide
- Publishing instructions
- 5 working examples
- Unit tests with pytest

## [Unreleased]

### Planned
- Web UI for monitoring (optional)
- Scheduled/cron-like tasks
- Task dependencies
- Result storage
- Performance optimizations
- More comprehensive test suite

[0.1.0]: https://github.com/ddreamboy/liteq/releases/tag/v0.1.0
