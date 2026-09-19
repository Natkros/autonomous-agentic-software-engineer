# Phase 4 Status

Scope per the project roadmap: filesystem tools, terminal tools, sandbox,
patch generation, test execution, retry logic.

## Done and verified

- [x] `sandbox/` — a `Sandbox` interface with two implementations:
  - `LocalProcessSandbox`: real, tested (`sandbox/tests/`), runs a
    subprocess with working-directory confinement, a hard timeout, and a
    minimal explicit environment (does not inherit host secrets).
  - `DockerSandbox`: real, complete code (`--network none`, memory/CPU
    limits, only the workspace mounted) — **unverified**, no live Docker
    daemon in this environment (Docker Desktop's CLI is present but its
    engine is not running here; `docker_daemon_available()` correctly
    detects this and falls back). See `sandbox/README.md` for the honest
    breakdown and what running it for real would require.
  - `get_default_sandbox()` picks Docker only after actually confirming a
    daemon responds (`docker info`), not just that the CLI exists.
- [x] `tools/filesystem/workspace.py` — a path-jailed `Workspace` wrapper
  used by every filesystem tool, rejecting `../` traversal, absolute-path
  escapes, and symlink tricks in one place. Tested directly with real
  escape attempts, not just happy-path reads/writes.
- [x] Five real filesystem tools: `filesystem.read`, `filesystem.list`
  (READ_ONLY), `filesystem.write`, `filesystem.delete` (SAFE_WRITE), and
  `filesystem.patch` (SAFE_WRITE) — structured patch application
  (create/replace/insert/delete) that computes and syntax-verifies the
  new file content **before** ever writing to disk, so a syntax-breaking
  patch is simply never applied (stronger than the spec's literal
  "backup then roll back," not a shortcut around it).
- [x] `terminal.execute` (EXECUTION) — runs a command through whichever
  `Sandbox` is available, confined to a `Workspace` root, and refuses
  anything not on an explicit binary allowlist (`pytest`, `npm`, `ruff`,
  `mypy`, `eslint`, `tsc`, `go`, `mvn`, `git`, etc.) before the sandbox
  ever sees the command.
- [x] `test.run` (EXECUTION) — runs pytest through the sandbox and parses
  real pass/fail/error/skip counts out of pytest's own summary line
  (not just a raw exit code), tested against real dynamically-generated
  passing and failing test files.
- [x] `core/orchestration/retry.py` — generic exponential-backoff retry,
  bounded (never loops forever), with injectable sleep for fast tests.
- [x] **A real end-to-end demonstration**
  (`tools/tests/test_apply_and_verify_integration.py`): copy a real
  repository into a temp workspace, apply a hand-written patch via
  `filesystem.patch`, then run its existing test suite via `test.run` and
  confirm it still passes — and confirm a syntax-breaking patch attempt
  is rejected before ever touching the file, leaving the original test
  suite green. Every tool call in the sequence lands in the same
  `AuditLog`.
- [x] Test count: `sandbox` 12, `tools` 52 (up from 12 in Phase 3) — all
  run in this session on Windows with Python 3.14.7.
- [x] CI now also runs `sandbox`'s suite.

**Post-Phase-5 correction:** `test.run` and `terminal.execute` originally
defaulted to `sandbox.factory.get_default_sandbox()` (Docker if a daemon
is reachable, else `LocalProcessSandbox`). This looked correct and passed
locally, but was a real bug: GitHub's `ubuntu-latest` CI runners have a
live Docker daemon by default (unlike this project's local dev
environment, where the daemon isn't running), so CI silently started
running `pytest`/allowlisted binaries inside a bare `python:3.12-slim`
container with none of those dependencies installed — and every such call
failed. Neither tool actually needs Docker's isolation to do its job
correctly (they need the CALLING environment's already-installed
dependencies via `sys.executable`/`PATH`), so both now default explicitly
to `LocalProcessSandbox` and no longer call `get_default_sandbox()` at
all. See `PHASE_5_STATUS.md` for how this was caught and fixed, and the
regression tests added to `tools/tests/test_run_tests_tool.py` and
`tools/tests/test_terminal_execute_tool.py` that lock the default in.

## Explicitly NOT done in Phase 4

- **`DockerSandbox.run_command()` has never been run against a live
  daemon.** Its command construction is unit-tested; its actual behavior
  under Docker (does `--network none` actually block network access? does
  `--memory`/`--cpus` actually get enforced? does `--rm` actually clean
  up?) is unverified. Do not deploy this expecting Docker-grade isolation
  until someone runs it for real — see `sandbox/README.md`.
- **The agent pipeline does not call any of these tools yet.** Phase 3's
  `CodingAgent` still only produces a `PatchProposal` *description*
  (heuristic text from `MockLLMProvider`, not real code) — automatically
  feeding that placeholder text into `filesystem.patch` would apply
  meaningless content to real files, so the pipeline and the Phase 4
  tools are deliberately NOT wired together yet. The
  `test_apply_and_verify_integration.py` test proves the *mechanism*
  works using a hand-written patch, not an agent-produced one.
- **No self-correction loop.** `retry_with_backoff` is a generic,
  reusable primitive (used nowhere in the pipeline yet) — the actual
  "run tests, if they fail classify why and try a different patch" loop
  described in the spec is Phase 5.
- **`filesystem.patch`'s backup/rollback is in-memory only, within one
  call.** There is no on-disk backup file and no cross-call undo. This is
  sufficient because verification always happens before any write, but it
  means there's no way to revert a patch that was already written and
  later found to be a mistake after the fact — that's a version-control
  concern (`git` — Phase 7), not this tool's job.
- **`terminal.execute`'s allowlist is a fixed Python set, not
  configurable per deployment or per autonomy level.** Anyone extending it
  needs to edit `ALLOWED_BINARIES` in code.
- **No `dependency.inspect`, `lint.run`, or `format.run` tools yet** —
  only the tools explicitly needed to demonstrate patch+test worked were
  built this phase.

## How to verify this yourself

```bash
cd sandbox && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 12 passed

cd ../tools && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 52 passed
```

To see whether Docker sandboxing actually works in your environment, start
a Docker daemon and re-run the `sandbox` suite — `docker_daemon_available()`
will pick it up automatically, and `sandbox/README.md` describes what to
check manually beyond that.
