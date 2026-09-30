import os
import sys
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.desktop.postgres_manager import PostgresManager


def test_postgres_readiness_transient_retries():
    pm = PostgresManager(port=5999)
    mock_responses = [
        (False, "OperationalError during startup: FATAL: the database system is starting up"),
        (False, "OperationalError during startup: FATAL: the database system is starting up"),
        (True, "Database connection test succeeded on DSN: 127.0.0.1:5999/postgres"),
    ]

    def mock_check():
        return mock_responses.pop(0) if mock_responses else (True, "Ready")

    with patch.object(pm, "check_readiness_detail", side_effect=mock_check):
        logs = []
        result = pm.wait_for_readiness(timeout_seconds=5, poll_interval=0.01, log_callback=lambda stage, msg: logs.append(msg))
        assert result is True
        assert any("ready and accepting connections" in m for m in logs)


def test_postgres_readiness_connection_refused_retries():
    pm = PostgresManager(port=5999)
    mock_responses = [
        (False, "OperationalError during startup: connection refused"),
        (True, "Database connection test succeeded"),
    ]

    def mock_check():
        return mock_responses.pop(0) if mock_responses else (True, "Ready")

    with patch.object(pm, "check_readiness_detail", side_effect=mock_check):
        result = pm.wait_for_readiness(timeout_seconds=5, poll_interval=0.01)
        assert result is True


def test_postgres_readiness_timeout():
    pm = PostgresManager(port=5999)
    with patch.object(pm, "check_readiness_detail", return_value=(False, "FATAL: the database system is starting up")):
        with pytest.raises(RuntimeError) as exc_info:
            pm.wait_for_readiness(timeout_seconds=0.1, poll_interval=0.01)
        assert "failed to become ready" in str(exc_info.value)


def test_postgres_already_running_no_second_start():
    pm = PostgresManager(port=5999)
    with patch.object(pm, "is_db_ready", return_value=True), \
         patch("subprocess.run") as mock_run, \
         patch("subprocess.Popen") as mock_popen:
        pm.start_server()
        mock_run.assert_not_called()
        mock_popen.assert_not_called()


def test_postgres_cluster_init_only_on_first_install(tmp_path):
    pm = PostgresManager(port=5999)
    pm.pg_data_dir = tmp_path

    # First run: PG_VERSION missing -> attempts initdb
    with patch.object(pm, "find_pg_binary", return_value=tmp_path / "initdb.exe"), \
         patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        pm.init_database_cluster()
        assert mock_run.call_count == 1

    # Second run: Create PG_VERSION -> skips initdb
    (tmp_path / "PG_VERSION").write_text("16")
    with patch("subprocess.run") as mock_run2:
        pm.init_database_cluster()
        mock_run2.assert_not_called()


def test_postgres_data_preservation(tmp_path):
    pm = PostgresManager(port=5999)
    pm.pg_data_dir = tmp_path
    version_file = tmp_path / "PG_VERSION"
    version_file.write_text("16")
    data_file = tmp_path / "custom_data.txt"
    data_file.write_text("historical user database records")

    pm.init_database_cluster()

    assert version_file.exists()
    assert version_file.read_text() == "16"
    assert data_file.exists()
    assert data_file.read_text() == "historical user database records"


def test_postgres_startup_sequence_order():
    calls = []

    pm = PostgresManager(port=5999)
    with patch.object(pm, "is_db_ready", return_value=False), \
         patch.object(pm, "is_port_open", return_value=False), \
         patch.object(pm, "find_pg_binary", return_value=Path("/tmp/pg_ctl")), \
         patch("subprocess.run", side_effect=lambda *args, **kwargs: calls.append("pg_ctl start") or MagicMock(returncode=0)), \
         patch.object(pm, "wait_for_readiness", side_effect=lambda *args, **kwargs: calls.append("wait_for_readiness") or True):
        pm.start_server()

    assert calls == ["pg_ctl start", "wait_for_readiness"]
