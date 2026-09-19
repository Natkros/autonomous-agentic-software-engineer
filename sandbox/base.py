"""The sandbox interface every command-execution path goes through.

The project's own security rule (spec section 16-17) is explicit: "Never
execute arbitrary commands directly on the host machine. All commands must
run inside an isolated Docker sandbox." This interface exists so that rule
has one enforcement point. See `docker_sandbox.py` and
`local_process_sandbox.py` for the two implementations and, critically,
`README.md` in this directory for which one is actually verified.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool

    @property
    def success(self) -> bool:
        return self.exit_code == 0 and not self.timed_out


class Sandbox(ABC):
    #: True for sandboxes that provide real OS-level isolation (a Docker
    #: container). False for anything that runs on the host process tree.
    provides_isolation: bool

    @abstractmethod
    def run_command(self, command: list[str], cwd: str, timeout_seconds: float, env: dict | None = None) -> SandboxResult:
        """Run ``command`` with ``cwd`` as its working directory. Must never
        raise for a command that runs and fails (nonzero exit) or times
        out — those are reported via ``SandboxResult``, not exceptions.
        Only genuine execution failures (e.g. the sandbox itself couldn't
        start) should raise.
        """
