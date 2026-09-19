"""Picks the best available sandbox, and is honest in its return value
about which one it picked (via `Sandbox.provides_isolation`) — callers
that need real isolation for genuinely untrusted input should check that
flag and refuse to proceed on a `LocalProcessSandbox`, rather than
silently accepting weaker guarantees.
"""
from __future__ import annotations

from sandbox.base import Sandbox
from sandbox.docker_sandbox import DockerSandbox, docker_daemon_available
from sandbox.local_process_sandbox import LocalProcessSandbox


def get_default_sandbox() -> Sandbox:
    if docker_daemon_available():
        return DockerSandbox()
    return LocalProcessSandbox()
