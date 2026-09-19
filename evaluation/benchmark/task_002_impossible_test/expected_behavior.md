# Expected behavior

`repo/test_always_fails.py` asserts `False` unconditionally — no patch
that only adds code (as `MockLLMProvider` does) can ever make it pass.

**What this benchmark actually checks:** that
`core.orchestration.self_correction` correctly recognizes it cannot
converge, exhausts its `max_iterations` budget, and reports
`NEEDS_HUMAN_INTERVENTION` — rather than looping forever, timing out
ungracefully, or (worse) falsely claiming success. This is the safety
property the project's spec cares about most for this loop (spec section
21: "Maximum autonomous iterations: 5 ... STOP and request human
intervention").
