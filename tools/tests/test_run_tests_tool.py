import os
import tempfile

from core.policies.permissions import AutonomyLevel
from sandbox.local_process_sandbox import LocalProcessSandbox
from tools.base import AuditLog
from tools.testing.run_tests_tool import RunTestsTool, parse_pytest_summary


def _write(root: str, name: str, content: str) -> None:
    with open(os.path.join(root, name), "w") as fh:
        fh.write(content)


def test_parse_pytest_summary_handles_mixed_results():
    counts = parse_pytest_summary("===== 2 failed, 3 passed, 1 skipped in 0.42s =====")
    assert counts == {"passed": 3, "failed": 2, "error": 0, "skipped": 1}


def test_parse_pytest_summary_handles_all_passed():
    counts = parse_pytest_summary("===== 5 passed in 0.10s =====")
    assert counts == {"passed": 5, "failed": 0, "error": 0, "skipped": 0}


def test_run_reports_all_tests_passing_on_a_real_passing_suite():
    with tempfile.TemporaryDirectory() as root:
        _write(root, "test_ok.py", "def test_one():\n    assert 1 + 1 == 2\n")
        result = RunTestsTool(sandbox=LocalProcessSandbox()).run(
            AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG, workspace_root=root,
        )
    assert result.success is True
    assert result.output["all_passed"] is True
    assert result.output["counts"]["passed"] == 1
    assert result.output["counts"]["failed"] == 0


def test_run_reports_failures_on_a_real_failing_suite():
    with tempfile.TemporaryDirectory() as root:
        _write(root, "test_broken.py", "def test_fails():\n    assert 1 == 2\n")
        result = RunTestsTool(sandbox=LocalProcessSandbox()).run(
            AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG, workspace_root=root,
        )
    assert result.success is True  # the TOOL succeeded; the test suite it ran did not
    assert result.output["all_passed"] is False
    assert result.output["counts"]["failed"] == 1


def test_run_reports_no_tests_collected_distinctly():
    with tempfile.TemporaryDirectory() as root:
        result = RunTestsTool(sandbox=LocalProcessSandbox()).run(
            AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG, workspace_root=root,
        )
    assert result.output["no_tests_collected"] is True
    assert result.output["all_passed"] is False


def test_default_constructor_uses_local_process_sandbox_not_docker():
    """Regression test: this tool must reuse the calling interpreter's
    already-installed pytest via `sys.executable`, never a bare Docker
    container with nothing installed. See the module docstring — this is
    what actually broke in CI (GitHub's ubuntu-latest runners have a live
    Docker daemon by default) until it was fixed.
    """
    assert isinstance(RunTestsTool().sandbox, LocalProcessSandbox)


def test_run_denied_below_execution_autonomy():
    with tempfile.TemporaryDirectory() as root:
        result = RunTestsTool(sandbox=LocalProcessSandbox()).run(
            AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=root,
        )
    assert result.success is False
    assert "requires permission" in result.error
