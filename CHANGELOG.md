# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
