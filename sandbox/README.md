# sandbox

The isolation layer the project's own spec requires before any
agent-generated command touches a filesystem: "Never execute arbitrary
commands directly on the host machine. All commands must run inside an
isolated Docker sandbox."

## Honest verification status

| Class | Isolation | Verified in this environment? |
|---|---|---|
| `LocalProcessSandbox` | None — runs as a subprocess of the host process, confined only by working-directory jailing (`tools/filesystem/workspace.py`), a command allowlist, a timeout, and a minimal explicit environment | **Yes** — real, tested (`tests/test_local_process_sandbox.py`) |
| `DockerSandbox` | Real — `--network none`, memory/CPU limits, only the workspace directory mounted | **No** — the code is complete and its command construction is unit-tested (`tests/test_docker_sandbox.py`), but `run_command()` has never actually been run against a live Docker daemon in this development environment |

`get_default_sandbox()` (`factory.py`) picks `DockerSandbox` only after
`docker_daemon_available()` actually invokes `docker info` and confirms a
daemon responds — not merely that the `docker` CLI exists on `PATH`. In
this development environment, Docker Desktop's CLI is installed but its
engine is not running, so `docker info` returns a nonzero exit code and
the factory correctly falls back to `LocalProcessSandbox`.

**Do not treat `LocalProcessSandbox` as meeting the project's own security
bar.** It is a real, working, tested mitigation — not the isolation the
spec calls for. Anything executed through it runs with the same
filesystem and network access as the ForgeAI process itself, restricted
only by the confinement measures listed above.

## To actually verify DockerSandbox

1. Start Docker Desktop (or any Docker daemon) so `docker info` exits 0.
2. Run `python -m pytest -v` again — `docker_daemon_available()` will now
   return `True`.
3. Manually exercise `DockerSandbox().run_command(...)` against a real
   command and confirm the container actually runs, respects
   `--network none`, and is torn down (`--rm`) afterward.

Nobody has done this yet in this project's development history. Update
this file once someone has, with what was actually observed.
