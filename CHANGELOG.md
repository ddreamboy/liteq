# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
