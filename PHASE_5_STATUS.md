# Phase 5 Status

Scope per the project roadmap: test agent, debugger, failure
classification, automatic patching, iterative execution (max 5
iterations).

## Done and verified

- [x] `agents/debugger/failure_classifier.py` — real, deterministic
  classification of a test run's actual stdout/stderr into one of the
  spec's 11 failure categories (SYNTAX_ERROR, TYPE_ERROR, IMPORT_ERROR,
  LOGIC_ERROR, TEST_ERROR, CONFIG_ERROR, DEPENDENCY_ERROR,
  ENVIRONMENT_ERROR, TIMEOUT, RESOURCE_ERROR, UNKNOWN). **Verified against
  genuinely broken code, not hand-crafted strings**: each test in
  `agents/tests/test_failure_classifier.py` writes an actually-broken
  Python file (a real `ModuleNotFoundError`, a real `TypeError`, a real
  bare-`assert` failure, a real `SyntaxError`), runs it through
  `test.run`, and classifies the genuine captured output. This caught a
  real bug during development: pytest rewrites a bare `assert x` into a
  report line with no literal "AssertionError" string at all — the
  classifier initially missed this and was fixed once the real-execution
  test caught it.
- [x] `agents/debugger/debugger_agent.py` — the `DebuggerAgent` always
  uses the real classifier for `failure_category` (overwriting whatever
  the LLM layer returns for that field), and only lets the LLM layer fill
  in narrative fields (root cause, evidence, proposed fix).
- [x] Schema additions (`core/state/schemas.py`): `FailureCategory`,
  `DebugReport`, `SelfCorrectionStatus`, `SelfCorrectionResult`. Also gave
  `PatchProposal` a `content` field (previously description-only) — see
  below.
- [x] `MockLLMProvider` now generates **real, syntactically valid Python
  content** for `.py` target files (a new stub function appended via
  `ast.parse`-verified text), not just placeholder description text. This
  is still a heuristic template, not real code generation — but it is
  genuinely valid Python that `filesystem.patch` can actually apply,
  which is what makes the rest of this phase possible to build and test
  for real rather than in theory.
- [x] `core/orchestration/self_correction.py` — the bounded loop:
  `CODE -> TEST -> PASS? -> (yes: done) / (no: diagnose -> patch -> retest)`,
  capped at `max_iterations` (default 5, per the spec's hard limit).
  **Never loops forever** — verified directly with a scenario
  engineered so no patch could ever make the test suite pass, confirming
  the loop stops exactly at the cap and reports
  `NEEDS_HUMAN_INTERVENTION` rather than looping indefinitely or raising.
  A second scenario confirms the loop recognizes success on the first
  iteration when a patch doesn't break anything.
- [x] Test count: `core` grew from 30 to 37 (new `test_llm_provider`
  cases + `test_self_correction.py`), `agents` grew from 9 to 19 (new
  `test_failure_classifier.py` + `test_debugger_agent.py`). **180 tests
  total** across all six suites, all run in this session, all verified
  fresh (clean `py -3.12` venvs matching CI, not just the pre-warmed
  shared dev venv).

## Explicitly NOT done in Phase 5

- **This is a mechanism test, not a demonstration of AI code-fixing
  quality.** With `MockLLMProvider` (the only provider exercised here),
  every patch attempt for a given task produces the same deterministic
  stub content — there is no real reasoning about *why* a test failed or
  *how* to fix it. A patch that fails will keep failing the same way on
  every iteration. The loop correctly detects this and gives up at the
  cap — which is itself the important, verified behavior — but nothing
  here should be read as "the AI debugged and fixed a real bug."
  Wiring `AnthropicLLMProvider` in (once a key is available) is what
  would make the *content* of each retry actually differ meaningfully.
- **No Test Engineer Agent that *generates* new tests.** Spec section 20
  describes an agent that writes unit/integration/API/regression/security
  tests for new functionality. This phase only *runs* existing tests
  (`test.run`, built in Phase 4) and classifies their failures — it does
  not write new test files.
- **No Code Review or Security Agent yet** to gate a self-corrected patch
  before it's considered "done" — those are Phase 6.
- **The self-correction loop is not wired into `/api/tasks`.** It exists
  as a real, tested, callable function
  (`core.orchestration.self_correction.run_self_correction_loop`) but the
  API pipeline (`core/orchestration/graph.py`) still stops after the
  Coding Agent proposes a patch, same as Phase 3/4. Wiring it in is
  straightforward but was left out to keep the API's behavior change
  deliberate and separately reviewable, not bundled into this phase.
- **`DEPENDENCY_ERROR` and `RESOURCE_ERROR` categories have real
  detection code but no test exercises them via genuinely broken code**
  (a real out-of-memory condition or a real missing system dependency is
  impractical to trigger reliably in a fast test suite) — their pattern
  matching is exercised structurally, not against a live failure, unlike
  every other category.

## A real bug CI caught after this phase's initial commit

The first push of this phase's work passed every local check (including
fresh Python 3.12 venvs) but **failed in CI**: `core`'s test suite failed
specifically because `core/orchestration/self_correction.py` calls
`RunTestsTool()` without specifying a sandbox, and that tool used to
default to `sandbox.factory.get_default_sandbox()` — which prefers Docker
whenever a daemon is reachable. GitHub's `ubuntu-latest` runners have a
live Docker daemon running by default; this project's local dev
environment does not. So locally, `test.run` always fell back to
`LocalProcessSandbox` (the only thing ever actually exercised here), while
in CI it silently switched to running `pytest` inside a bare
`python:3.12-slim` container that has no `pytest` installed — every real
test-execution call failed, which broke the self-correction loop's
counts and its test assertions.

Fixed by making `test.run` and `terminal.execute` default explicitly to
`LocalProcessSandbox` (see `PHASE_4_STATUS.md`) instead of ever silently
preferring Docker, since neither tool's job (reusing the calling
environment's already-installed dependencies) is served by an unprovisioned
container. This is exactly the kind of gap the "verify in a fresh venv
matching CI" discipline from the Phase 3 incident does NOT catch — it was
an environment-configuration difference (is Docker running?), not a
dependency-installation difference — so CI itself, not local verification,
is what caught it. That is a real limitation of local-only checking worth
remembering for later phases.

## How to verify this yourself

```bash
cd core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 37 passed

cd ../agents && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 19 passed
```

Both were verified in this session in clean `py -3.12` virtual
environments (matching what CI actually runs), not only the shared,
pre-warmed development venv — the Phase 3 CI failure this project hit
earlier came from exactly that gap, so every phase from here on is
double-checked this way before being called done.
