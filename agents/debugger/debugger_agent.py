"""The Debugger Agent: classifies a failed test run and produces a
DebugReport (spec section 22).

The `failure_category` is always the real, deterministic classification
from `failure_classifier.py` — the agent overwrites whatever the LLM layer
returns for that field, so a heuristic/mock provider can never silently
mis-tag a real SyntaxError as something else. Only the narrative fields
(root cause, evidence, proposed fix) come from the LLM layer.
"""
from __future__ import annotations

from agents.debugger.failure_classifier import classify_failure
from core.providers.llm_provider import LLMProvider
from core.state.schemas import DebugReport, Task

_SYSTEM_PROMPT = """You are a debugging engineer investigating a failed test run.
You are given the real, already-determined failure category, the task
that was being implemented, and an excerpt of the actual test output.
Explain the likely root cause, cite the evidence for it, and propose a
fix. Do not invent a different failure category than the one given.
Respond only via the provided schema."""


class DebuggerAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def diagnose(self, test_output: dict, task: Task, iteration: int = 0) -> DebugReport:
        category = classify_failure(
            stdout=test_output.get("stdout", ""),
            stderr=test_output.get("stderr", ""),
            timed_out=test_output.get("timed_out", False),
        )

        prompt = "\n".join([
            f"failure_category: {category.value}",
            f"task: {task.description}",
            f"output_excerpt: {test_output.get('stdout', '')[-1000:]}",
        ])

        report = self.llm_provider.generate_structured(
            system_prompt=_SYSTEM_PROMPT, user_prompt=prompt, schema=DebugReport,
        )
        # Never trust the LLM layer over the real classifier for this field.
        report.failure_category = category
        report.iteration = iteration
        return report
