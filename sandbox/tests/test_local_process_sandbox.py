import sys
import tempfile

from sandbox.local_process_sandbox import LocalProcessSandbox


def test_runs_a_command_and_captures_stdout():
    sandbox = LocalProcessSandbox()
    with tempfile.TemporaryDirectory() as cwd:
        result = sandbox.run_command([sys.executable, "-c", "print('hello')"], cwd=cwd, timeout_seconds=10)
    assert result.success is True
    assert result.exit_code == 0
    assert "hello" in result.stdout


def test_reports_nonzero_exit_code_without_raising():
    sandbox = LocalProcessSandbox()
    with tempfile.TemporaryDirectory() as cwd:
        result = sandbox.run_command([sys.executable, "-c", "import sys; sys.exit(3)"], cwd=cwd, timeout_seconds=10)
    assert result.success is False
    assert result.exit_code == 3
    assert result.timed_out is False


def test_enforces_timeout():
    sandbox = LocalProcessSandbox()
    with tempfile.TemporaryDirectory() as cwd:
        result = sandbox.run_command(
            [sys.executable, "-c", "import time; time.sleep(5)"], cwd=cwd, timeout_seconds=0.3,
        )
    assert result.timed_out is True
    assert result.success is False


def test_does_not_inherit_full_host_environment_by_default(monkeypatch):
    monkeypatch.setenv("FORGEAI_TEST_SECRET", "should-not-be-visible")
    sandbox = LocalProcessSandbox()
    with tempfile.TemporaryDirectory() as cwd:
        result = sandbox.run_command(
            [sys.executable, "-c", "import os; print(os.environ.get('FORGEAI_TEST_SECRET', 'MISSING'))"],
            cwd=cwd, timeout_seconds=10,
        )
    assert "MISSING" in result.stdout


def test_explicit_env_is_used_verbatim():
    sandbox = LocalProcessSandbox()
    with tempfile.TemporaryDirectory() as cwd:
        result = sandbox.run_command(
            [sys.executable, "-c", "import os; print(os.environ.get('CUSTOM_VAR', 'MISSING'))"],
            cwd=cwd, timeout_seconds=10, env={"CUSTOM_VAR": "present"},
        )
    assert "present" in result.stdout


def test_provides_isolation_is_honestly_false():
    assert LocalProcessSandbox().provides_isolation is False
