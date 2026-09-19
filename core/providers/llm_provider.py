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

from core.state.schemas import Plan, PatchOperation, PatchProposal, RequirementAnalysis, RiskLevel, Task

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
    def _patch_proposal(user_prompt: str) -> PatchProposal:
        """Expects lines ``task_id: <id>``, ``task: <description>``, and
        ``candidate_file: <path>`` — see ``agents/coder/coding_agent.py``.
        """
        fields = {}
        for line in user_prompt.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                fields[key.strip().lower()] = value.strip()

        return PatchProposal(
            task_id=fields.get("task_id", "TASK-001"),
            file=fields.get("candidate_file", "UNKNOWN"),
            operation=PatchOperation.REPLACE,
            description=f"Implement: {fields.get('task', 'the requested change')}",
            rationale="Heuristic proposal from MockLLMProvider — verify against the real codebase before applying.",
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
