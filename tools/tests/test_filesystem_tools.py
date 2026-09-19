import os
import tempfile

import pytest

from core.policies.permissions import AutonomyLevel
from tools.base import AuditLog
from tools.filesystem.list_tool import FilesystemListTool
from tools.filesystem.read_tool import FilesystemReadTool
from tools.filesystem.write_tool import FilesystemDeleteTool, FilesystemWriteTool


@pytest.fixture()
def workspace_root():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "existing.txt"), "w") as fh:
            fh.write("original")
        yield root


def test_read_tool_reads_existing_file(workspace_root):
    result = FilesystemReadTool().run(
        AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=workspace_root, path="existing.txt",
    )
    assert result.success is True
    assert result.output["content"] == "original"


def test_read_tool_fails_for_missing_file(workspace_root):
    result = FilesystemReadTool().run(
        AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=workspace_root, path="missing.txt",
    )
    assert result.success is False


def test_list_tool_lists_directory(workspace_root):
    result = FilesystemListTool().run(
        AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=workspace_root, path=".",
    )
    assert result.success is True
    assert "existing.txt" in result.output["entries"]


def test_write_tool_requires_safe_write_autonomy(workspace_root):
    result = FilesystemWriteTool().run(
        AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY,
        workspace_root=workspace_root, path="new.txt", content="hi",
    )
    assert result.success is False
    assert "requires permission" in result.error


def test_write_tool_creates_file_at_sufficient_autonomy(workspace_root):
    result = FilesystemWriteTool().run(
        AuditLog(), AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES,
        workspace_root=workspace_root, path="new.txt", content="hi there",
    )
    assert result.success is True
    with open(os.path.join(workspace_root, "new.txt")) as fh:
        assert fh.read() == "hi there"


def test_delete_tool_removes_file_at_sufficient_autonomy(workspace_root):
    result = FilesystemDeleteTool().run(
        AuditLog(), AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES,
        workspace_root=workspace_root, path="existing.txt",
    )
    assert result.success is True
    assert not os.path.exists(os.path.join(workspace_root, "existing.txt"))


def test_write_tool_rejects_path_escaping_workspace(workspace_root):
    result = FilesystemWriteTool().run(
        AuditLog(), AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES,
        workspace_root=workspace_root, path="../../escape.txt", content="pwned",
    )
    assert result.success is False
