import pytest

from core.providers.llm_provider import (
    AnthropicLLMProvider,
    LLMProviderError,
    MockLLMProvider,
    get_default_llm_provider,
)
from core.state.schemas import Plan, PatchProposal, RequirementAnalysis


def test_mock_provider_extracts_requirement_analysis_from_multi_sentence_request():
    provider = MockLLMProvider()
    result = provider.generate_structured(
        system_prompt="",
        user_prompt="Add JWT authentication. Create login and registration endpoints. Do not break existing tests.",
        schema=RequirementAnalysis,
    )
    assert isinstance(result, RequirementAnalysis)
    assert result.task == "Add JWT authentication."
    assert any("login" in r.lower() for r in result.requirements)
    assert any("break" in c.lower() for c in result.constraints)
    assert len(result.acceptance_criteria) == len(result.requirements[:5])


def test_mock_provider_flags_ambiguity_for_very_short_requests():
    provider = MockLLMProvider()
    result = provider.generate_structured(system_prompt="", user_prompt="fix it", schema=RequirementAnalysis)
    assert result.ambiguities


def test_mock_provider_builds_plan_from_requirement_lines():
    provider = MockLLMProvider()
    prompt = "task: Add auth\nrequirement: add login endpoint\nrequirement: add password hashing"
    plan = provider.generate_structured(system_prompt="", user_prompt=prompt, schema=Plan)
    assert isinstance(plan, Plan)
    assert len(plan.tasks) == 2
    assert plan.tasks[1].dependencies == [plan.tasks[0].id]
    assert plan.has_valid_dependencies()


def test_mock_provider_flags_higher_risk_for_security_sensitive_tasks():
    provider = MockLLMProvider()
    plan = provider.generate_structured(
        system_prompt="", user_prompt="requirement: add password reset flow", schema=Plan
    )
    assert plan.tasks[0].risk.value == "high"


def test_mock_provider_builds_patch_proposal():
    provider = MockLLMProvider()
    prompt = "task_id: TASK-001\ntask: add health endpoint\ncandidate_file: app/main.py"
    proposal = provider.generate_structured(system_prompt="", user_prompt=prompt, schema=PatchProposal)
    assert isinstance(proposal, PatchProposal)
    assert proposal.file == "app/main.py"
    assert proposal.task_id == "TASK-001"


def test_mock_provider_raises_for_unregistered_schema():
    from pydantic import BaseModel

    class SomeOtherSchema(BaseModel):
        x: int

    provider = MockLLMProvider()
    with pytest.raises(LLMProviderError):
        provider.generate_structured(system_prompt="", user_prompt="", schema=SomeOtherSchema)


def test_anthropic_provider_without_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    provider = AnthropicLLMProvider()
    with pytest.raises(LLMProviderError):
        provider.generate_structured(system_prompt="", user_prompt="", schema=RequirementAnalysis)


def test_default_provider_falls_back_to_mock_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert isinstance(get_default_llm_provider(), MockLLMProvider)
