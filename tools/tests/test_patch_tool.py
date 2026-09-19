import os
import tempfile

import pytest

from core.policies.permissions import AutonomyLevel
from core.state.schemas import PatchOperation
from tools.base import AuditLog
from tools.filesystem.patch_tool import FilesystemPatchTool


@pytest.fixture()
def workspace_root():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "app.py"), "w") as fh:
            fh.write("def health_check():\n    return {'status': 'ok'}\n")
        yield root


def _run(workspace_root, **kwargs):
    return FilesystemPatchTool().run(
        AuditLog(), AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES, workspace_root=workspace_root, **kwargs,
    )


def test_create_file_writes_new_valid_python_file(workspace_root):
    result = _run(
        workspace_root, path="new_module.py", operation=PatchOperation.CREATE_FILE,
        content="def add(a, b):\n    return a + b\n",
    )
    assert result.success is True
    with open(os.path.join(workspace_root, "new_module.py")) as fh:
        assert "def add" in fh.read()


def test_create_file_rejects_invalid_python_syntax_and_writes_nothing(workspace_root):
    result = _run(
        workspace_root, path="broken.py", operation=PatchOperation.CREATE_FILE,
        content="def broken(:\n    pass\n",
    )
    assert result.success is False
    assert "invalid Python syntax" in result.error
    assert not os.path.exists(os.path.join(workspace_root, "broken.py"))


def test_create_file_refuses_to_overwrite_existing_file(workspace_root):
    result = _run(workspace_root, path="app.py", operation=PatchOperation.CREATE_FILE, content="x = 1\n")
    assert result.success is False


def test_replace_whole_file_when_no_line_range_given(workspace_root):
    result = _run(
        workspace_root, path="app.py", operation=PatchOperation.REPLACE,
        content="def health_check():\n    return {'status': 'healthy'}\n",
    )
    assert result.success is True
    with open(os.path.join(workspace_root, "app.py")) as fh:
        assert "healthy" in fh.read()


def test_replace_line_range_preserves_surrounding_lines(workspace_root):
    with open(os.path.join(workspace_root, "multi.py"), "w") as fh:
        fh.write("a = 1\nb = 2\nc = 3\n")

    result = _run(
        workspace_root, path="multi.py", operation=PatchOperation.REPLACE,
        content="b = 200\n", start_line=2, end_line=2,
    )
    assert result.success is True
    with open(os.path.join(workspace_root, "multi.py")) as fh:
        assert fh.read() == "a = 1\nb = 200\nc = 3\n"


def test_replace_rejects_patch_that_breaks_syntax_and_leaves_file_untouched(workspace_root):
    original = open(os.path.join(workspace_root, "app.py")).read()

    result = _run(
        workspace_root, path="app.py", operation=PatchOperation.REPLACE,
        content="def health_check(:\n", start_line=1, end_line=1,
    )
    assert result.success is False
    with open(os.path.join(workspace_root, "app.py")) as fh:
        assert fh.read() == original


def test_insert_adds_lines_without_removing_existing_content(workspace_root):
    with open(os.path.join(workspace_root, "multi.py"), "w") as fh:
        fh.write("a = 1\nc = 3\n")

    result = _run(
        workspace_root, path="multi.py", operation=PatchOperation.INSERT,
        content="b = 2\n", start_line=2,
    )
    assert result.success is True
    with open(os.path.join(workspace_root, "multi.py")) as fh:
        assert fh.read() == "a = 1\nb = 2\nc = 3\n"


def test_delete_removes_specified_line_range(workspace_root):
    with open(os.path.join(workspace_root, "multi.py"), "w") as fh:
        fh.write("a = 1\nb = 2\nc = 3\n")

    result = _run(
        workspace_root, path="multi.py", operation=PatchOperation.DELETE,
        start_line=2, end_line=2,
    )
    assert result.success is True
    with open(os.path.join(workspace_root, "multi.py")) as fh:
        assert fh.read() == "a = 1\nc = 3\n"


def test_non_python_files_are_written_without_syntax_verification(workspace_root):
    result = _run(
        workspace_root, path="notes.txt", operation=PatchOperation.CREATE_FILE,
        content="this is not python at all {{{",
    )
    assert result.success is True


def test_patch_denied_below_safe_write_autonomy(workspace_root):
    result = FilesystemPatchTool().run(
        AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY,
        workspace_root=workspace_root, path="app.py", operation=PatchOperation.REPLACE,
        content="x = 1\n",
    )
    assert result.success is False
    assert "requires permission" in result.error
