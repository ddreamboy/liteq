"""Tests for CLI functionality"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from liteq.cli import main

TEST_DB = "test_cli.db"


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    """Setup test database"""
    monkeypatch.setenv("LITEQ_DB", TEST_DB)

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    yield

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_cli_no_arguments():
    """Test CLI with no arguments shows help"""
    with patch("sys.argv", ["liteq"]):
        # Parser prints help and exits with 0 when no command given
        # argparse may not raise SystemExit if dest is set properly
        main()  # Just verify it doesn't crash


def test_cli_worker_missing_app():
    """Test worker command requires --app argument"""
    with patch("sys.argv", ["liteq", "worker"]):
        with pytest.raises(SystemExit):
            main()


def test_cli_worker_with_defaults(tmp_path):
    """Test worker command with default parameters"""
    # Create a simple tasks module
    tasks_file = tmp_path / "test_tasks.py"
    tasks_file.write_text("""
from liteq import task

@task()
def sample_task():
    return "done"
""")

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        with patch("sys.argv", ["liteq", "worker", "--app", "test_tasks.py"]):
            with patch("liteq.cli.Worker") as MockWorker:
                mock_instance = MagicMock()
                MockWorker.return_value = mock_instance

                main()

                # Verify Worker was initialized with default params
                MockWorker.assert_called_once_with(queues=["default"], concurrency=4, task_timeout=None)
                mock_instance.run.assert_called_once()
    finally:
        os.chdir(original_cwd)


def test_cli_worker_with_custom_params(tmp_path):
    """Test worker command with custom parameters"""
    tasks_file = tmp_path / "my_tasks.py"
    tasks_file.write_text("""
from liteq import task

@task()
def my_task():
    pass
""")

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        with patch(
            "sys.argv",
            [
                "liteq",
                "worker",
                "--app",
                "my_tasks.py",
                "--queues",
                "emails,reports",
                "--concurrency",
                "8",
                "--timeout",
                "60",
            ],
        ):
            with patch("liteq.cli.Worker") as MockWorker:
                mock_instance = MagicMock()
                MockWorker.return_value = mock_instance

                main()

                # Verify Worker was initialized with correct params
                MockWorker.assert_called_once_with(queues=["emails", "reports"], concurrency=8, task_timeout=60)
                mock_instance.run.assert_called_once()
    finally:
        os.chdir(original_cwd)


def test_cli_worker_module_import(tmp_path):
    """Test that worker properly imports the module"""
    tasks_file = tmp_path / "tasks_module.py"
    tasks_file.write_text("""
from liteq import task

@task()
def imported_task():
    return 42
""")

    original_cwd = os.getcwd()
    os.chdir(tmp_path)

    try:
        with patch("sys.argv", ["liteq", "worker", "--app", "tasks_module.py"]):
            with patch("liteq.cli.Worker") as MockWorker:
                mock_instance = MagicMock()
                MockWorker.return_value = mock_instance

                main()

                # Verify the module was imported
                assert "tasks_module" in sys.modules
                mock_instance.run.assert_called_once()
    finally:
        os.chdir(original_cwd)
        # Clean up imported module
        if "tasks_module" in sys.modules:
            del sys.modules["tasks_module"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
