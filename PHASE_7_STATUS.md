# Phase 7 Status

Scope per the project roadmap: branches, commits, diffs, pull requests,
approval workflow.

## Done and verified

- [x] `tools/git/git_repo.py` — a thin, real wrapper around the system
  `git` binary (same approach as `code_intelligence/indexing/git_ingest.py`),
  with six real tools built on top of it:
  - **READ_ONLY**: `git.status`, `git.diff`, `git.log`
  - **GIT_WRITE**: `git.branch`, `git.commit`, `git.push`
  
  Every single one is tested against a real, freshly-`git init`'d
  repository — no mocks. `git.push` is verified against a real local
  **bare** repository acting as the remote (`git init --bare`), then the
  test independently re-reads the bare repo's own log to confirm the
  commit actually landed there, rather than trusting the tool's return
  value alone.
- [x] `core/policies/approval.py` — `build_approval_request()`, the human
  approval prompt described in spec section 27 (reason, files affected,
  commands, risk level). Whether approval is required is a deterministic
  function of `PermissionLevel` vs. `AutonomyLevel` (Phase 3's policy
  engine) — never an LLM's judgment call. `DEPLOYMENT`-level actions
  always produce an approval request, confirmed even at the maximum
  autonomy level.
- [x] `tools/git/github_client.py` — `GitHubPullRequestClient`, a real,
  complete implementation of GitHub's "create a pull request" REST API
  call. Same honest pattern as `AnthropicLLMProvider` and
  `OpenAIEmbeddingProvider` from earlier phases: real code, gated behind
  `GITHUB_TOKEN`, and **not exercised** — no network access or GitHub
  token in this development environment. What's actually tested is that
  it raises a clear error without a token and accepts an explicit token
  override.
- [x] New schemas: `ApprovalRequest`, `ApprovalStatus`, `GitCommitRecord`,
  `GitStatusEntry`.
- [x] Test count: `tools` grew from 80 to 94, `core` grew from 37 to 41.
  **235 tests total** across all six suites (`code_intelligence` 40,
  `core` 41, `sandbox` 12, `tools` 94, `agents` 28, `apps/api` 20),
  re-verified in clean Python 3.12 venvs matching CI.

## Explicitly NOT done in Phase 7

- **No pull request has ever actually been opened.** `GitHubPullRequestClient.create_pull_request()`
  is real, complete code that has never been run against the live GitHub
  API in this environment. Do not treat it as verified.
- **The full branch -> commit -> push -> PR -> approval workflow is not
  wired together as a single orchestrated function**, and it is not
  connected to `core/orchestration/graph.py` or the API. Each piece
  (branching, committing, pushing, requesting approval, opening a PR) is
  real and independently tested, but nothing yet calls them in sequence
  as one "ship this change" operation — that step also requires the
  Phase 5/6 self-correction and review/security results to feed into the
  approval request's risk assessment, which hasn't been built either.
- **No merge, rebase, or conflict-resolution tooling.** Only the specific
  operations the spec calls for (branch/commit/diff/log/status/push) were
  built. A real merge conflict during any of these would surface as a
  generic `GitCommandError`, not a specially-handled case.
- **The approval workflow has no UI.** `build_approval_request()`
  produces the structured data section 27's UI mockup describes
  (reason/files/commands/risk level with approve/reject/modify), but
  there is no dashboard, CLI prompt, or API endpoint that actually
  presents it to a human and collects a decision — `ApprovalStatus`
  starts at `PENDING` and nothing transitions it to `APPROVED`/`REJECTED`
  yet.
- **No branch-protection or force-push safety checks.** `git.push` will
  push whatever it's told to; there's no logic here preventing a push to
  a protected branch like `main` (that's expected to be enforced by the
  remote's own branch protection rules, same as for a human contributor,
  not re-implemented client-side).

## How to verify this yourself

```bash
cd tools && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 94 passed

cd ../core && python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt && python -m pytest -v   # 41 passed
```

To actually verify `GitHubPullRequestClient`: set `GITHUB_TOKEN` to a
real personal access token with `repo` scope, point it at a real
repository you control, and manually call `create_pull_request(...)`
after pushing a branch with `git.push`. Nobody has done this yet in this
project's development history.
