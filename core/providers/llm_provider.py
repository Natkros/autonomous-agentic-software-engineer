"""LLM provider abstraction.

Same pattern as `code_intelligence/providers/embeddings.py` in Phase 2: a
small interface, a real offline deterministic fallback that this project's
own test suite actually exercises, and a real network-calling
implementation that has NOT been exercised in this environment (no network
or API key here) — do not treat it as verified until someone runs it.

``MockLLMProvider`` is a deterministic, rule-based stand-in for a real LLM.
It does not understand language — it applies fixed heuristics (sentence
splitting, keyword matching, templating) to produce schema-valid output
that is genuinely derived from its input, not hardcoded. This is what lets
the full agent pipeline in this phase run and be tested end-to-end without
any API key. It is not a substitute for real reasoning, and its output
quality should not be judged as if it were.
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from core.state.schemas import (
    DebugReport,
    FailureCategory,
    Plan,
    PatchOperation,
    PatchProposal,
    RequirementAnalysis,
    RiskLevel,
    Task,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class LLMProviderError(RuntimeError):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[SchemaT]) -> SchemaT:
        """Return an instance of ``schema`` derived from the prompts."""


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_STOPWORDS = {"the", "a", "an", "and", "or", "to", "of", "for", "in", "on", "that", "this", "with"}


class MockLLMProvider(LLMProvider):
    """See module docstring. Dispatches on the requested schema type."""

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[SchemaT]) -> SchemaT:
        if schema is RequirementAnalysis:
            return self._requirement_analysis(user_prompt)  # type: ignore[return-value]
        if schema is Plan:
            return self._plan(user_prompt)  # type: ignore[return-value]
        if schema is PatchProposal:
            return self._patch_proposal(user_prompt)  # type: ignore[return-value]
        if schema is DebugReport:
            return self._debug_report(user_prompt)  # type: ignore[return-value]
        raise LLMProviderError(f"MockLLMProvider has no heuristic for schema {schema.__name__}")

    @staticmethod
    def _requirement_analysis(user_prompt: str) -> RequirementAnalysis:
        sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(user_prompt) if s.strip()]
        task = sentences[0] if sentences else user_prompt.strip()

        requirements = []
        constraints = []
        for sentence in sentences:
            lowered = sentence.lower()
            if any(word in lowered for word in ("don't", "do not", "must not", "without breaking", "existing")):
                constraints.append(sentence)
            elif sentence != task:
                requirements.append(sentence)

        if not requirements and sentences:
            # A single-sentence request IS its own requirement.
            requirements = [task]

        acceptance_criteria = [f"'{req}' is implemented and covered by a passing test" for req in requirements[:5]]

        ambiguities = []
        if len(sentences) <= 1 and len(user_prompt.split()) < 6:
            ambiguities.append("The request is very short; consider asking the user for more detail before planning.")

        return RequirementAnalysis(
            task=task,
            requirements=requirements,
            constraints=constraints,
            acceptance_criteria=acceptance_criteria,
            ambiguities=ambiguities,
        )

    @staticmethod
    def _plan(user_prompt: str) -> Plan:
        """Expects ``user_prompt`` to contain lines of the form
        ``requirement: <text>`` (built by the Planning Agent) — see
        ``agents/planner/planner_agent.py`` for how the prompt is composed.
        """
        requirement_lines = [
            line.split(":", 1)[1].strip()
            for line in user_prompt.splitlines()
            if line.lower().startswith("requirement:")
        ]
        if not requirement_lines:
            requirement_lines = ["Implement the requested change"]

        tasks = []
        for i, requirement in enumerate(requirement_lines, start=1):
            task_id = f"TASK-{i:03d}"
            dependencies = [f"TASK-{i - 1:03d}"] if i > 1 else []
            risk = RiskLevel.HIGH if any(w in requirement.lower() for w in ("auth", "security", "password", "delete")) else RiskLevel.MEDIUM
            tasks.append(Task(id=task_id, description=requirement, dependencies=dependencies, risk=risk))

        return Plan(tasks=tasks)

    @staticmethod
    def _slugify_function_name(text: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
        slug = re.sub(r"_+", "_", slug)[:40] or "change"
        if slug[0].isdigit():
            slug = f"_{slug}"
        return slug

    @classmethod
    def _patch_proposal(cls, user_prompt: str) -> PatchProposal:
        """Expects lines ``task_id: <id>``, ``task: <description>``, and
        ``candidate_file: <path>`` — see ``agents/coder/coding_agent.py``.

        For a Python target file, this generates real, syntactically valid
        (if trivial) content: a new stub function appended to the file —
        not because it's a good implementation of the task, but because it
        lets Phase 4/5's apply-and-test machinery actually exercise a real
        file write. For any other file type, no content is generated
        (`content=None`) since there's no safe generic template to offer.
        """
        fields = {}
        for line in user_prompt.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip().lower()] = value.strip()

        task_text = fields.get("task", "the requested change")
        candidate_file = fields.get("candidate_file", "UNKNOWN")

        content = None
        operation = PatchOperation.REPLACE
        if candidate_file.endswith(".py"):
            function_name = f"handle_{cls._slugify_function_name(task_text)}"
            content = f'\n\ndef {function_name}():\n    """Auto-generated stub for: {task_text}"""\n    pass\n'
            operation = PatchOperation.INSERT

        return PatchProposal(
            task_id=fields.get("task_id", "TASK-001"),
            file=candidate_file,
            operation=operation,
            description=f"Implement: {task_text}",
            rationale="Heuristic proposal from MockLLMProvider — verify against the real codebase before applying.",
            content=content,
        )

    @staticmethod
    def _debug_report(user_prompt: str) -> DebugReport:
        """Expects lines ``failure_category: <value>``, ``task: <description>``,
        and ``output_excerpt: <text>`` — see ``agents/debugger/debugger_agent.py``.
        The category itself always comes from the real, deterministic
        classifier in ``agents/debugger/failure_classifier.py``, never from
        this heuristic — this only fills in the narrative fields.
        """
        fields = {}
        for line in user_prompt.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip().lower()] = value.strip()

        category_raw = fields.get("failure_category", FailureCategory.UNKNOWN.value)
        try:
            category = FailureCategory(category_raw)
        except ValueError:
            category = FailureCategory.UNKNOWN

        excerpt = fields.get("output_excerpt", "")[:300]
        return DebugReport(
            failure_category=category,
            root_cause=f"Test run failed with a classified {category.value.replace('_', ' ')}; see evidence.",
            evidence=excerpt or "No output captured.",
            proposed_fix=(
                f"Review the {category.value.replace('_', ' ')} in {fields.get('task', 'the failing task')} "
                "and adjust the proposed patch accordingly."
            ),
        )


class AnthropicLLMProvider(LLMProvider):
    """Real implementation against Anthropic's Messages API, using tool-use
    to force schema-shaped JSON output. Requires ANTHROPIC_API_KEY.

    NOT exercised in this project's test suite (no network/API key in this
    environment) — verify manually before relying on it in production.
    """

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        self.model = model
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: type[SchemaT]) -> SchemaT:
        if not self.api_key:
            raise LLMProviderError(
                "ANTHROPIC_API_KEY is not set; cannot call the Anthropic API. "
                "Use MockLLMProvider for offline/local development instead."
            )

        tool_name = f"emit_{schema.__name__.lower()}"
        payload = json.dumps({
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "tools": [{
                "name": tool_name,
                "description": f"Emit a {schema.__name__} object.",
                "input_schema": schema.model_json_schema(),
            }],
            "tool_choice": {"type": "tool", "name": tool_name},
        }).encode("utf-8")

        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=payload,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                body = json.loads(response.read())
        except Exception as exc:
            raise LLMProviderError(f"Anthropic API request failed: {exc}") from exc

        for block in body.get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == tool_name:
                return schema.model_validate(block["input"])

        raise LLMProviderError("Anthropic response did not include the expected tool_use block")


def get_default_llm_provider() -> LLMProvider:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return AnthropicLLMProvider()
    return MockLLMProvider()
