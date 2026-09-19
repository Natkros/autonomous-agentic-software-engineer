"""Real Docker-based sandboxing — the isolation level the project's spec
actually calls for: no host filesystem access beyond the mounted workspace,
no network, and CPU/memory limits.

NOT exercised in this environment (no Docker daemon available here — see
`PHASE_1_STATUS.md`). Do not treat this as verified until someone runs it
against a real Docker daemon. `get_default_sandbox()` in `factory.py`
only selects this class after confirming a daemon actually responds.
"""
from __future__ import annotations

import shutil
import subprocess

from sandbox.base import Sandbox, SandboxResult

DEFAULT_IMAGE = "python:3.12-slim"


class DockerSandbox(Sandbox):
    provides_isolation = True

    def __init__(self, image: str = DEFAULT_IMAGE, memory_limit: str = "512m", cpu_limit: str = "1"):
        self.image = image
        self.memory_limit = memory_limit
        self.cpu_limit = cpu_limit

    def _build_docker_command(self, command: list[str], cwd: str, env: dict | None = None) -> list[str]:
        docker_command = [
            "docker", "run", "--rm",
            "--network", "none",
            "--memory", self.memory_limit,
            "--cpus", self.cpu_limit,
            "-v", f"{cwd}:/workspace",
            "-w", "/workspace",
        ]
        for key, value in (env or {}).items():
            docker_command += ["-e", f"{key}={value}"]
        docker_command.append(self.image)
        docker_command += command
        return docker_command

    def run_command(self, command: list[str], cwd: str, timeout_seconds: float, env: dict | None = None) -> SandboxResult:
        docker_command = self._build_docker_command(command, cwd, env)

        try:
            completed = subprocess.run(
                docker_command, timeout=timeout_seconds, capture_output=True, text=True,
            )
            return SandboxResult(
                exit_code=completed.returncode, stdout=completed.stdout, stderr=completed.stderr, timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                exit_code=-1,
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                timed_out=True,
            )


def docker_daemon_available() -> bool:
    """A real, live check — not just "is the docker CLI on PATH" — that
    actually confirms a daemon responds, so `get_default_sandbox()` never
    silently claims Docker isolation it can't provide.
    """
    if shutil.which("docker") is None:
        return False
    try:
        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False
