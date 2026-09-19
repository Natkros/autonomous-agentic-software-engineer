"""Token/cost tracking (spec section 35).

`estimate_tokens()` is a rough heuristic (roughly 4 characters per token,
the commonly-cited approximation for English text), NOT a real tokenizer
— this project has no dependency on `tiktoken` or Anthropic's own
tokenizer. It is only accurate enough for order-of-magnitude cost
estimates, and is explicitly labeled as such everywhere it's used.

`MODEL_PRICING` is illustrative, publicly-published per-token pricing for
a couple of real model families, current as of when this was written —
NOT fetched live, and will drift out of date. `MockLLMProvider` calls are
tracked at $0.00 because they are not real API calls at all — assigning
them a nonzero cost would be actively misleading.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# USD per token (not per 1K/1M) for prompt (input) and completion (output),
# so callers don't need to remember a denominator. Illustrative only.
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-5-20250929": (3.00 / 1_000_000, 15.00 / 1_000_000),
    "mock": (0.0, 0.0),
}
_UNKNOWN_MODEL_PRICING = (0.0, 0.0)


def estimate_tokens(text: str) -> int:
    """~4 characters per token — a rough heuristic, not a real tokenizer."""
    return max(1, len(text) // 4) if text else 0


@dataclass
class LLMCallCost:
    model: str
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float
    latency_ms: float


class CostTracker:
    """Accumulates cost/latency across every LLM call in a run (or an
    entire evaluation session) so per-task and aggregate totals are always
    computed from the same real record, not re-derived inconsistently.
    """

    def __init__(self) -> None:
        self._calls: list[LLMCallCost] = []

    def record(self, model: str, input_tokens: int, output_tokens: int, latency_ms: float) -> LLMCallCost:
        input_price, output_price = MODEL_PRICING.get(model, _UNKNOWN_MODEL_PRICING)
        cost = input_tokens * input_price + output_tokens * output_price
        call = LLMCallCost(
            model=model, input_tokens=input_tokens, output_tokens=output_tokens,
            estimated_cost_usd=cost, latency_ms=latency_ms,
        )
        self._calls.append(call)
        return call

    @property
    def calls(self) -> list[LLMCallCost]:
        return list(self._calls)

    @property
    def total_cost_usd(self) -> float:
        return sum(c.estimated_cost_usd for c in self._calls)

    @property
    def total_tokens(self) -> int:
        return sum(c.input_tokens + c.output_tokens for c in self._calls)

    @property
    def call_count(self) -> int:
        return len(self._calls)
