# Phase 2 Status

Scope per the project roadmap: repository ingestion, file tree analysis,
code parsing, AST analysis, symbol extraction, code indexing, vector
search.

## Done and verified

- [x] New standalone `code_intelligence` package (see
      [`code_intelligence/README.md`](code_intelligence/README.md) for the
      full module-by-module breakdown) — **40/40 tests pass**, run in this
      session.
- [x] File tree analysis: language detection, config/test/entry-point
      classification, ignored-directory filtering (`.git`, `node_modules`,
      `.venv`, build output, etc).
- [x] Real AST-based symbol extraction for **Python** (stdlib `ast`) and
      **JavaScript/JSX** (`esprima`, a pure-Python ECMAScript parser) —
      functions, classes, methods, decorators, base classes, docstrings,
      imports.
- [x] Best-effort, explicitly-labeled **heuristic** (regex, not AST)
      extraction for TypeScript/TSX, since no pure-Python TS parser exists.
- [x] Dependency parsing (`requirements.txt`, `package.json`,
      `pyproject.toml`) and framework detection (FastAPI, Next.js, React,
      SQLAlchemy, Django, Flask, Express, and others) from those
      dependencies.
- [x] README summary extraction, API route detection (FastAPI decorator
      patterns), and database model detection (SQLAlchemy/Django-style base
      classes).
- [x] A file-level **import graph** (not a call graph — see
      `code_intelligence/graph/dependency_graph.py` for the explicit scope
      limit) with reverse lookups ("who imports this file").
- [x] An embedding provider abstraction: `LocalHashEmbedding` (real,
      deterministic, offline — actually used and tested) and
      `OpenAIEmbeddingProvider` (real code, not yet exercised — see below).
- [x] A vector index abstraction: Qdrant in embedded mode (no server
      process required) with a pure-Python brute-force cosine-similarity
      fallback if Qdrant is unavailable.
- [x] A hybrid retriever blending semantic + keyword + symbol + file-path
      search into one ranked list, tested against the project's own stated
      example query ("find code responsible for user authentication").
- [x] **API integration**: `POST /api/repositories/{id}/analyze` clones the
      repository's URL with the real `git` binary and runs the scanner
      against it; `GET /api/repositories/{id}/analysis` returns the latest
      result. A new `repository_analyses` table stores each run
      (`COMPLETED` with a JSON summary, or `FAILED` with an error message —
      a bad/unreachable URL is a recorded outcome, not a 500).
- [x] Backend test suite grew from 9 to **14 tests**, including a full
      end-to-end analyze flow that clones a real, freshly-`git init`'d local
      fixture repository (no network dependency, no mocks) and asserts on
      the actual extracted symbols and detected frameworks.

## Explicitly NOT done in Phase 2

- **No call graph.** Only import-level file relationships are resolved.
  "Which functions call this method?" (one of the project's stated design
  goals) is not answerable yet — it needs cross-file name-binding
  resolution, which is a substantially larger undertaking.
- **`OpenAIEmbeddingProvider` is unverified.** The code is real and
  complete, but there is no network access or API key in this development
  environment, so it has never actually been run. Do not treat it as
  working until someone runs it with a real key.
- **No background indexing job.** `/analyze` runs synchronously on the
  request thread and blocks until the clone+scan finishes. A large
  repository will make this endpoint slow. Moving this to a Celery/Redis
  background worker is Phase 4 scope (`sandbox`/execution infrastructure),
  not Phase 2.
- **`code_intelligence` is not packaged as an installable dependency.**
  `apps/api/app/services/analysis_service.py` reaches it by inserting the
  repository root onto `sys.path` at import time — a documented, deliberate
  simplification (see that file's docstring), not an oversight. It also
  means the current `infrastructure/docker/api.Dockerfile` (which only
  copies `apps/api`) would need `code_intelligence` added to its build
  context before `/analyze` would work inside the Docker Compose stack —
  this has not been done or tested.
- **Only Python, JavaScript, and TypeScript have symbol extraction.**
  `parsers/language.py` classifies many more file types by extension, but
  Java/Go/Rust/C++/etc. are detected as files only, with no symbol
  extraction.
- **No vector persistence across runs.** Each `/analyze` call rebuilds the
  scanner's in-process results from scratch; nothing is written into
  Qdrant/a persistent vector store tied to a repository ID yet — the
  hybrid retriever exists and is tested as a library, but isn't wired into
  a stored, queryable index behind an API endpoint.

## How to verify this yourself

```bash
# code_intelligence package (standalone)
cd code_intelligence
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements-dev.txt
python -m pytest -v          # 40 passed

# apps/api (now depends on code_intelligence too)
cd ../apps/api
source .venv/Scripts/activate    # reuse the same venv if you installed
                                  # esprima/qdrant-client into it, or
                                  # pip install -r requirements-dev.txt fresh
python -m pytest -v          # 14 passed
```

Both suites were run in this session on Windows with Python 3.14.7. The
integration test in `apps/api/tests/test_repository_analysis.py` requires
the `git` executable on `PATH` (used to clone a local fixture repo — no
network access needed).
