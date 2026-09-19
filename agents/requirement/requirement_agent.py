"""The Requirement Analyst Agent: turns a natural-language task into a
structured, validated RequirementAnalysis (see spec section 7)."""
from __future__ import annotations

from core.providers.llm_provider import LLMProvider
from core.state.schemas import RequirementAnalysis

_SYSTEM_PROMPT = """You are a requirement analyst on a software engineering team.
Given a user's natural-language request, extract:
- the core task in one sentence
- a list of discrete functional/non-functional requirements
- a list of constraints (things that must NOT change or break)
- acceptance criteria for each requirement
- any ambiguities that should be clarified with the user before implementation begins
Respond only via the provided schema."""


class RequirementAnalystAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def analyze(self, user_request: str) -> RequirementAnalysis:
        return self.llm_provider.generate_structured(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_request,
            schema=RequirementAnalysis,
        )
