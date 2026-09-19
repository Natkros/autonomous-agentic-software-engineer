import os
import tempfile

import pytest

from tools.filesystem.workspace import PathEscapesWorkspaceError, Workspace


@pytest.fixture()
def workspace():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "sub"))
        with open(os.path.join(root, "sub", "file.txt"), "w") as fh:
            fh.write("hello")
        yield Workspace(root)


def test_read_text_returns_file_contents(workspace):
    assert workspace.read_text("sub/file.txt") == "hello"


def test_read_text_raises_for_missing_file(workspace):
    with pytest.raises(FileNotFoundError):
        workspace.read_text("does-not-exist.txt")


def test_write_text_creates_parent_directories(workspace):
    workspace.write_text("new/nested/dir/file.txt", "content")
    assert workspace.read_text("new/nested/dir/file.txt") == "content"


def test_write_text_overwrites_existing_file(workspace):
    workspace.write_text("sub/file.txt", "updated")
    assert workspace.read_text("sub/file.txt") == "updated"


def test_delete_file_removes_it(workspace):
    workspace.delete_file("sub/file.txt")
    assert workspace.exists("sub/file.txt") is False


def test_delete_file_refuses_directories(workspace):
    with pytest.raises(IsADirectoryError):
        workspace.delete_file("sub")


def test_list_dir_returns_sorted_entries(workspace):
    workspace.write_text("a.txt", "1")
    workspace.write_text("z.txt", "2")
    entries = workspace.list_dir(".")
    assert entries == sorted(entries)
    assert "a.txt" in entries and "z.txt" in entries


def test_resolve_rejects_parent_directory_escape(workspace):
    with pytest.raises(PathEscapesWorkspaceError):
        workspace.resolve("../../etc/passwd")


def test_resolve_rejects_absolute_path_outside_workspace(workspace):
    with pytest.raises(PathEscapesWorkspaceError):
        workspace.resolve("/etc/passwd" if os.name != "nt" else "C:\\Windows\\System32\\config")


def test_resolve_allows_paths_within_workspace(workspace):
    resolved = workspace.resolve("sub/file.txt")
    assert resolved.startswith(workspace.root)
