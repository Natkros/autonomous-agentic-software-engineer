# code_intelligence

Phase 2 of the ForgeAI roadmap: repository understanding, AST-based symbol
extraction, dependency/framework detection, and hybrid code search. This is
a standalone, independently testable Python package — it does not depend on
`apps/api`, though `apps/api` imports it (see
`apps/api/app/services/analysis_service.py`) to back the
`POST /api/repositories/{id}/analyze` endpoint.

## What's real here

| Module | What it does | How it's verified |
|---|---|---|
| `parsers/language.py` | Language detection by extension, config/test/entry-point classification | `tests/test_language.py` |
| `ast_tools/python_extractor.py` | Real AST-based extraction (functions, classes, methods, decorators, bases, docstrings, imports) via the stdlib `ast` module | `tests/test_python_extractor.py` |
| `ast_tools/javascript_extractor.py` | Real AST-based extraction for JS/JSX via `esprima` (a pure-Python ECMAScript parser) | `tests/test_javascript_extractor.py` |
| `ast_tools/typescript_heuristic.py` | **Regex-based, best-effort** extraction for TS/TSX — documented explicitly as not a real parse (no pure-Python TypeScript parser exists) | `tests/test_typescript_heuristic.py` |
| `indexing/repository_scanner.py` | Walks a directory tree: file classification, dependency parsing (`requirements.txt`/`package.json`/`pyproject.toml`), framework detection, README summary, API route detection (FastAPI decorators), DB model detection (SQLAlchemy/Django-style base classes) | `tests/test_repository_scanner.py` |
| `indexing/git_ingest.py` | Clones a git URL or local path via the system `git` binary | Exercised end-to-end by `apps/api/tests/test_repository_analysis.py` (clones a real, freshly `git init`'d local fixture repo — no network needed) |
| `graph/dependency_graph.py` | File-level **import** graph (not a call graph — see module docstring for the explicit scope limit) | `tests/test_dependency_graph.py` |
| `providers/embeddings.py` | `LocalHashEmbedding` (deterministic, offline, real) + `OpenAIEmbeddingProvider` (real code, **not exercised** — no network/API key in this environment) | `tests/test_embeddings.py` |
| `indexing/vector_index.py` | Qdrant in embedded mode (no server process), falling back to a pure-Python brute-force cosine index if Qdrant is unavailable | `tests/test_vector_index.py` |
| `retrieval/hybrid_search.py` | Blends semantic + keyword + symbol + file-path search into one ranked result list | `tests/test_hybrid_search.py` |

Run the suite:

```bash
cd code_intelligence
python -m venv .venv && source .venv/Scripts/activate   # or .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -v
```

## Explicitly out of scope for this phase

- **Call graphs.** Only import-level relationships are resolved ("which
  files import this module"), not "which functions call this function" —
  that requires cross-file name-binding resolution, which is a larger
  undertaking left for later.
- **TypeScript AST.** No pure-Python TypeScript parser exists; full
  TS/TSX support would mean shelling out to the TypeScript compiler or a
  Node-based parser, which this phase deliberately avoids to keep the
  package's dependency footprint (and offline testability) minimal.
- **Learned embeddings by default.** `LocalHashEmbedding` is a real,
  deterministic bag-of-tokens hash, good enough to rank "similar vocabulary"
  above "unrelated," but it is not a trained semantic model. Swap in
  `OpenAIEmbeddingProvider` (or another `EmbeddingProvider` implementation)
  once real embeddings are needed and a key is available.
- **Languages beyond Python/JavaScript/TypeScript.** `parsers/language.py`
  recognizes many extensions for file classification, but only these three
  have symbol extractors.

## Package naming note

The AST module is named `ast_tools/`, not `ast/`, specifically to avoid
shadowing Python's standard library `ast` module once this package's
directory ends up on `sys.path` (which happens both under pytest and via
the `apps/api` integration) — naming it `ast/` breaks every stdlib import
of `ast` anywhere else in the process, including deep inside `pytest`
itself. This was caught by actually running the test suite, not by
inspection.
