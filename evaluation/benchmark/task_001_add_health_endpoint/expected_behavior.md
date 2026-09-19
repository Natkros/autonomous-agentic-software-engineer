# Expected behavior

A real, capable coding agent would add a `/health`-style endpoint to
`repo/app.py` and the existing test suite would continue to pass.

**What this benchmark actually checks in this environment:** with
`MockLLMProvider` (the only provider ever exercised here), the "patch"
is a deterministic stub function, not a real endpoint. This task
verifies the mechanism, not the outcome: given a task whose patch is
purely additive, does `core.orchestration.self_correction` recognize
success on the first iteration rather than needlessly retrying or
misreporting failure? See `evaluation_criteria.json` and
`../../runner.py`'s module docstring.
