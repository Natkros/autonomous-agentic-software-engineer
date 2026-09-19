import ast

import pytest

from core.providers.llm_provider import (
    AnthropicLLMProvider,
    LLMProviderError,
    MockLLMProvider,
    get_default_llm_provider,
)
from core.state.schemas import DebugReport, FailureCategory, Plan, PatchOperation, PatchProposal, RequirementAnalysis


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


def test_mock_provider_generates_real_syntactically_valid_python_content_for_py_files():
    provider = MockLLMProvider()
    prompt = "task_id: TASK-001\ntask: add health endpoint\ncandidate_file: app/main.py"
    proposal = provider.generate_structured(system_prompt="", user_prompt=prompt, schema=PatchProposal)

    assert proposal.operation == PatchOperation.INSERT
    assert proposal.content is not None
    ast.parse(proposal.content)  # must be real, valid Python — not just any string


def test_mock_provider_generates_distinct_function_names_per_task():
    provider = MockLLMProvider()
    proposal_a = provider.generate_structured(
        system_prompt="", user_prompt="task_id: A\ntask: add login\ncandidate_file: app/main.py", schema=PatchProposal,
    )
    proposal_b = provider.generate_structured(
        system_prompt="", user_prompt="task_id: B\ntask: add logout\ncandidate_file: app/main.py", schema=PatchProposal,
    )
    assert proposal_a.content != proposal_b.content


def test_mock_provider_generates_no_content_for_non_python_files():
    provider = MockLLMProvider()
    prompt = "task_id: TASK-001\ntask: update styling\ncandidate_file: app/styles.css"
    proposal = provider.generate_structured(system_prompt="", user_prompt=prompt, schema=PatchProposal)
    assert proposal.content is None
    assert proposal.operation == PatchOperation.REPLACE


def test_mock_provider_builds_debug_report_using_given_failure_category():
    provider = MockLLMProvider()
    prompt = "failure_category: import_error\ntask: add health endpoint\noutput_excerpt: ModuleNotFoundError: no module named foo"
    report = provider.generate_structured(system_prompt="", user_prompt=prompt, schema=DebugReport)

    assert isinstance(report, DebugReport)
    assert report.failure_category == FailureCategory.IMPORT_ERROR
    assert "ModuleNotFoundError" in report.evidence


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


def test_anthropic_provider_surfaces_the_apis_actual_error_message(monkeypatch):
    """Regression test for a real bug found against the live Anthropic API
    (a 400 from an exhausted credit balance): the original exception
    handler discarded urllib's response body, so every failure surfaced as
    the generic "HTTP Error 400: Bad Request" — useless for diagnosing
    what actually went wrong. Anthropic's real error body has the shape
    reproduced here.
    """
    import io
    import urllib.error

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    provider = AnthropicLLMProvider()

    real_error_body = (
        b'{"type":"error","error":{"type":"invalid_request_error",'
        b'"message":"Your credit balance is too low to access the Anthropic API."}}'
    )

    def _raise_http_error(*args, **kwargs):
        raise urllib.error.HTTPError(
            url="https://api.anthropic.com/v1/messages", code=400, msg="Bad Request",
            hdrs=None, fp=io.BytesIO(real_error_body),
        )

    monkeypatch.setattr("urllib.request.urlopen", _raise_http_error)

    with pytest.raises(LLMProviderError, match="credit balance is too low"):
        provider.generate_structured(system_prompt="", user_prompt="", schema=RequirementAnalysis)
