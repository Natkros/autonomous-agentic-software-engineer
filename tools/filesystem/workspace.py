"""A path-jailed view over a directory on disk.

Every filesystem tool in this package goes through a `Workspace` rather
than touching `open()`/`os.remove()` directly, so path-traversal
(`../../etc/passwd`-style escapes, absolute paths, and symlink tricks) is
rejected in exactly one place instead of being re-implemented (and
possibly re-broken) per tool.
"""
from __future__ import annotations

import os


class PathEscapesWorkspaceError(ValueError):
    pass


class Workspace:
    def __init__(self, root: str):
        if not os.path.isdir(root):
            raise NotADirectoryError(root)
        self.root = os.path.realpath(root)

    def resolve(self, relative_path: str) -> str:
        """Return an absolute path guaranteed to be inside this workspace,
        or raise PathEscapesWorkspaceError.
        """
        candidate = os.path.realpath(os.path.join(self.root, relative_path))
        # os.path.commonpath raises on mixed drive letters (Windows); treat
        # that as an escape rather than letting the exception propagate.
        try:
            if os.path.commonpath([self.root, candidate]) != self.root:
                raise PathEscapesWorkspaceError(f"'{relative_path}' resolves outside the workspace")
        except ValueError as exc:
            raise PathEscapesWorkspaceError(f"'{relative_path}' resolves outside the workspace") from exc
        return candidate

    def exists(self, relative_path: str) -> bool:
        return os.path.exists(self.resolve(relative_path))

    def read_text(self, relative_path: str) -> str:
        path = self.resolve(relative_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(relative_path)
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()

    def write_text(self, relative_path: str, content: str) -> int:
        path = self.resolve(relative_path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            return fh.write(content)

    def delete_file(self, relative_path: str) -> None:
        path = self.resolve(relative_path)
        if os.path.isdir(path):
            raise IsADirectoryError(f"refusing to delete a directory: {relative_path}")
        if not os.path.isfile(path):
            raise FileNotFoundError(relative_path)
        os.remove(path)

    def list_dir(self, relative_path: str = ".") -> list[str]:
        path = self.resolve(relative_path)
        if not os.path.isdir(path):
            raise NotADirectoryError(relative_path)
        return sorted(os.listdir(path))
