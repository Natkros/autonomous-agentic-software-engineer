"""The Planning Agent: turns a RequirementAnalysis + RepositorySummary into
an executable Plan (a task DAG), per spec section 12."""
from __future__ import annotations

from core.providers.llm_provider import LLMProvider
from core.state.schemas import Plan, RepositorySummary, RequirementAnalysis

_SYSTEM_PROMPT = """You are a software engineering planner.
Given a set of requirements and a summary of the target repository, produce
an ordered list of implementation tasks. Each task must have a unique id,
a clear description, its dependencies (other task ids that must complete
first), the files it likely touches, and a risk level. Respond only via
the provided schema."""


class PlanInvalidError(ValueError):
    pass


class PlanningAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def plan(self, requirement_analysis: RequirementAnalysis, repository_summary: RepositorySummary) -> Plan:
        prompt_lines = [f"task: {requirement_analysis.task}"]
        for requirement in requirement_analysis.requirements:
            prompt_lines.append(f"requirement: {requirement}")
        for constraint in requirement_analysis.constraints:
            prompt_lines.append(f"constraint: {constraint}")
        prompt_lines.append(f"repository_frameworks: {', '.join(repository_summary.frameworks) or 'none detected'}")
        prompt_lines.append(f"repository_key_files: {', '.join(repository_summary.key_files) or 'none'}")

        result = self.llm_provider.generate_structured(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt="\n".join(prompt_lines),
            schema=Plan,
        )

        if not result.has_valid_dependencies():
            raise PlanInvalidError(
                f"Plan contains a task dependency that doesn't reference a known task id: {result.model_dump()}"
            )
        return result
