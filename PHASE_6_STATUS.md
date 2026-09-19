# Phase 6 Status

Scope per the project roadmap: review agent, static analysis, security
agent, dependency scanning, quality checks.

## Done and verified

- [x] `tools/security/static_analysis.py` — real AST-based static
  analysis for Python (spec section 25's static-analysis half): detects
  `eval`/`exec`, `subprocess(..., shell=True)`, bare `except:`, insecure
  `pickle.load(s)`, `yaml.load()` without an explicit safe `Loader`,
  SQL built via string formatting passed to `.execute(...)`, and
  hardcoded credential-shaped assignments. **No LLM involved** — this is
  structural pattern matching over an actual parsed AST, the same
  approach as `code_intelligence`'s symbol extractor. Every rule is
  tested against both genuinely vulnerable code and genuinely clean code
  that must NOT trigger a false positive (e.g. `subprocess.run([...])`
  without `shell=True`, parameterized queries, `except ValueError:`).
- [x] `tools/security/secret_scanner.py` — regex-based credential-shape
  detection (AWS access key IDs, PEM private key headers, Slack tokens,
  GitHub tokens, generic `password=`/`api_key=`-style assignments) over
  any text file, not just Python. Tested against real-shaped (fake,
  invalid) example secrets and confirmed silent on clean text.
- [x] `security.scan` (`tools/security/security_scan_tool.py`) — a
  READ_ONLY tool that walks an entire workspace, runs both scanners over
  every file, and reports whether any BLOCKER/HIGH finding exists
  (`blocks_finalization`), per the spec's requirement that severe
  security findings block finalization.
- [x] `SecurityAgent` (`agents/security/security_agent.py`) —
  deterministic, no LLM call: the same principle already applied to the
  Repository Explorer Agent in Phase 3 (a direct computation doesn't need
  a model call to get the same answer).
- [x] `CodeReviewAgent` (`agents/reviewer/review_agent.py`) — reviews
  only a `PatchProposal`'s actual `content` (the diff, per spec section
  24's "review only the diff"), also deterministic. Runs the same static
  analysis + secret scanning against the proposed change, plus one
  quality check: it correctly flags `MockLLMProvider`'s own generated
  stub patches (`def handle_...(): pass`) as an unimplemented stub — a
  genuinely true finding about this project's own current LLM layer, not
  a contrived example.
- [x] New shared schemas: `Severity` (BLOCKER/HIGH/MEDIUM/LOW/INFO, used
  by both review and security findings, per spec), `ReviewFinding`,
  `ReviewResult` (`.approved` is a computed property — never something an
  LLM merely asserts), `SecurityFinding`, `SecurityScanResult`.
- [x] Test count: `tools` grew from 52 to 80, `agents` grew from 19 to
  28. **217 tests total** across all six suites
  (`code_intelligence` 40, `core` 37, `sandbox` 12, `tools` 80,
  `agents` 28, `apps/api` 20).

## Explicitly NOT done in Phase 6

- **No dependency-vulnerability scanning against a real advisory
  database.** The spec mentions Semgrep/Bandit/Trivy/Gitleaks-style
  scanning; this phase's static analysis and secret scanner are original,
  dependency-free implementations covering a deliberately small rule set
  (documented in each module's docstring) — not a wrapper around one of
  those real tools, and not a check against live CVE data (no network
  access to a vulnerability feed in this environment). A production
  system would layer this with a real scanner rather than replace it.
- **These are syntactic heuristics, not dataflow/taint analysis.** A
  determined obfuscation (e.g. building `"ev"+"al"` and calling
  `getattr(builtins, ...)`) evades every rule here. This is a real,
  permanent limitation of AST-pattern rules in general, called out
  explicitly in `static_analysis.py`'s docstring.
- **Review/Security agents are not wired into the pipeline or the API.**
  `core/orchestration/graph.py` (used by `/api/tasks`) still stops after
  the Coding Agent proposes a patch; nothing currently calls
  `CodeReviewAgent` or `SecurityAgent` automatically. They exist as real,
  tested, callable components, consistent with how Phase 4's tools and
  Phase 5's self-correction loop were built standalone before any
  pipeline integration.
- **No Documentation Agent or Final Validator.** Those remain empty
  placeholders (`agents/documentation`, `agents/validator`), along with
  `agents/architecture` and `agents/tester` (test *generation*, as
  opposed to test *execution* from Phase 4/5).
- **The secret scanner's pattern list is small and provider-specific.**
  It will miss any credential shape not in its list (e.g. a generic
  32-character hex API key with no recognizable prefix) — it is not an
  entropy-based detector, a deliberate choice to keep the false-positive
  rate low in a small implementation, documented in the module.

## How to verify this yourself

```bash
cd tools && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 80 passed

cd ../agents && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 28 passed
```

Both re-verified in clean Python 3.12 virtual environments matching CI —
see `PHASE_5_STATUS.md` for why that discipline exists (a real CI failure
on the previous phase's push, caught by CI itself rather than local
checks, since it was an environment-configuration difference: whether a
Docker daemon happens to be running).
