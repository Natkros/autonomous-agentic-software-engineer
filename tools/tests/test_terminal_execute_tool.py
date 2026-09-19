import sys
import tempfile

from core.policies.permissions import AutonomyLevel
from sandbox.local_process_sandbox import LocalProcessSandbox
from tools.base import AuditLog
from tools.terminal.terminal_execute_tool import TerminalExecuteTool


def test_allowed_binary_runs_successfully():
    with tempfile.TemporaryDirectory() as root:
        tool = TerminalExecuteTool(sandbox=LocalProcessSandbox())
        result = tool.run(
            AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
            workspace_root=root, command=["python", "-c", "print('ran')"],
        )
    assert result.success is True
    assert result.output["exit_code"] == 0
    assert "ran" in result.output["stdout"]


def test_disallowed_binary_is_refused_before_running():
    with tempfile.TemporaryDirectory() as root:
        tool = TerminalExecuteTool(sandbox=LocalProcessSandbox())
        result = tool.run(
            AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
            workspace_root=root, command=["rm", "-rf", "/"],
        )
    assert result.success is False
    assert "not in the allowed command list" in result.error


def test_denied_below_execution_autonomy():
    with tempfile.TemporaryDirectory() as root:
        tool = TerminalExecuteTool(sandbox=LocalProcessSandbox())
        result = tool.run(
            AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY,
            workspace_root=root, command=["python", "-c", "print(1)"],
        )
    assert result.success is False
    assert "requires permission" in result.error


def test_reports_sandbox_isolation_flag_honestly():
    with tempfile.TemporaryDirectory() as root:
        tool = TerminalExecuteTool(sandbox=LocalProcessSandbox())
        result = tool.run(
            AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
            workspace_root=root, command=["python", "-c", "print(1)"],
        )
    assert result.output["sandbox_provided_isolation"] is False


def test_default_constructor_uses_local_process_sandbox_not_docker():
    """Regression test for a real bug this project hit: GitHub's
    `ubuntu-latest` CI runners have a live Docker daemon by default (unlike
    local dev here), so silently defaulting to `get_default_sandbox()`
    made this tool try to run allowlisted binaries inside a bare Docker
    container that doesn't have them installed. See the module docstring.
    """
    assert isinstance(TerminalExecuteTool().sandbox, LocalProcessSandbox)


def test_command_is_confined_to_the_workspace_cwd():
    with tempfile.TemporaryDirectory() as root:
        tool = TerminalExecuteTool(sandbox=LocalProcessSandbox())
        result = tool.run(
            AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
            workspace_root=root, command=["python", "-c", "import os; print(os.getcwd())"],
        )
    import os
    assert os.path.realpath(root) in result.output["stdout"]
