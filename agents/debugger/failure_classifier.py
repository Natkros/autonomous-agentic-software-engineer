"""Real, deterministic failure classification (spec section 22) from a
test run's actual captured stdout/stderr — pattern matching over genuine
pytest/Python traceback text, not an LLM guess. This is what lets the
Debugger Agent's `failure_category` field be trusted even though the rest
of its narrative (root cause prose, proposed fix wording) comes from the
LLM layer, which in this environment is the heuristic `MockLLMProvider`.

Order matters: more specific patterns are checked before generic ones
(e.g. `ModuleNotFoundError` before a generic `Error` check) so a single
traceback with several substrings doesn't get misclassified by whichever
check happens to run first.
"""
from __future__ import annotations

import re

from core.state.schemas import FailureCategory

_PATTERNS: list[tuple[str, FailureCategory]] = [
    ("SyntaxError", FailureCategory.SYNTAX_ERROR),
    ("IndentationError", FailureCategory.SYNTAX_ERROR),
    ("ModuleNotFoundError", FailureCategory.IMPORT_ERROR),
    ("ImportError", FailureCategory.IMPORT_ERROR),
    ("TypeError", FailureCategory.TYPE_ERROR),
    ("MemoryError", FailureCategory.RESOURCE_ERROR),
    ("ConnectionError", FailureCategory.ENVIRONMENT_ERROR),
    ("PermissionError", FailureCategory.ENVIRONMENT_ERROR),
    ("FileNotFoundError", FailureCategory.ENVIRONMENT_ERROR),
    ("no tests ran", FailureCategory.CONFIG_ERROR),
    ("error collecting", FailureCategory.CONFIG_ERROR),
    ("AssertionError", FailureCategory.TEST_ERROR),
]

# pytest rewrites a bare `assert x` inside a test into a report line of the
# form "E   assert 1 == 2" — no literal "AssertionError" string appears at
# all in that case, so the plain substring check above misses it.
_PYTEST_ASSERT_LINE_RE = re.compile(r"^E\s+assert\b", re.MULTILINE)


def classify_failure(stdout: str, stderr: str, timed_out: bool) -> FailureCategory:
    if timed_out:
        return FailureCategory.TIMEOUT

    combined = f"{stdout}\n{stderr}"
    for needle, category in _PATTERNS:
        if needle.lower() in combined.lower():
            return category

    if _PYTEST_ASSERT_LINE_RE.search(combined):
        return FailureCategory.TEST_ERROR

    if not combined.strip():
        return FailureCategory.UNKNOWN

    # Something failed and produced output, but nothing matched a known
    # pattern — a real (if generic) logic failure, not an unknown one.
    return FailureCategory.LOGIC_ERROR
