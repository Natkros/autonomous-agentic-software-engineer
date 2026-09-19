"""Runs commands as a subprocess of the current host process.

This is NOT the Docker sandbox the project's spec calls for — it provides
no filesystem, network, or user isolation from the host. It exists as the
fallback used automatically when Docker isn't available (see
`get_default_sandbox()` in `factory.py`), with three real, enforced
mitigations instead of true isolation:

1. Working directory confinement — the caller passes a ``cwd``, and
   `tools/terminal/terminal_execute_tool.py` requires that ``cwd`` to be
   inside a `Workspace` (see `tools/filesystem/workspace.py`), so a command
   cannot be pointed at an arbitrary host path.
2. A hard wall-clock timeout via `subprocess.run(..., timeout=...)`.
3. A minimal, explicit environment — the current process's full
   environment is NOT inherited, only what's passed in `env`.

Combined with the command allowlist in `terminal_execute_tool.py`, this
meaningfully reduces (but does not eliminate) risk. Do not treat it as
safe for genuinely untrusted or adversarial input — that requires the real
`DockerSandbox`, which exists but is unverified in this environment (see
`sandbox/README.md`).
"""
from __future__ import annotations

import os
import subprocess

from sandbox.base import Sandbox, SandboxResult

# The only variables inherited from the host when the caller doesn't supply
# an explicit `env` — enough for `python`/`pytest`/`npm` etc. to be found
# and to run, without inheriting API keys, tokens, or other ambient secrets
# the calling process might have.
_SAFE_ENV_PASSTHROUGH = ("PATH", "PATHEXT", "SYSTEMROOT", "HOME", "USERPROFILE", "TEMP", "TMP")


def _minimal_env() -> dict:
    return {key: os.environ[key] for key in _SAFE_ENV_PASSTHROUGH if key in os.environ}


class LocalProcessSandbox(Sandbox):
    provides_isolation = False

    def run_command(self, command: list[str], cwd: str, timeout_seconds: float, env: dict | None = None) -> SandboxResult:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                timeout=timeout_seconds,
                capture_output=True,
                text=True,
                env=env if env is not None else _minimal_env(),
            )
            return SandboxResult(
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                exit_code=-1,
                stdout=exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or ""),
                stderr=exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or ""),
                timed_out=True,
            )
