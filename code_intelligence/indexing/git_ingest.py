"""Minimal repository ingestion: clone a Git URL (or copy a local path) into
a workspace directory so it can be scanned.

This is intentionally a thin, single-purpose helper for Phase 2 indexing —
it is NOT the permissioned, audited tool system described for Phase 4
(``tools/git``). It shells out to the system ``git`` binary rather than
using GitPython, to avoid adding a dependency for a single command.
"""
from __future__ import annotations

import shutil
import subprocess


class GitCloneError(RuntimeError):
    pass


def clone_repository(source: str, destination: str, depth: int = 1) -> str:
    """Clone ``source`` (a git URL or local path) into ``destination``.

    Returns the destination path on success. Raises GitCloneError on failure
    (invalid URL, network unavailable, auth required, etc.) with the
    underlying git stderr for diagnosis.
    """
    if shutil.which("git") is None:
        raise GitCloneError("git executable not found on PATH")

    command = ["git", "clone", "--depth", str(depth), source, destination]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise GitCloneError(result.stderr.strip() or "git clone failed")
    return destination
