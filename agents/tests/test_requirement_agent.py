from agents.requirement.requirement_agent import RequirementAnalystAgent
from core.providers.llm_provider import MockLLMProvider
from core.state.schemas import RequirementAnalysis


def test_requirement_agent_returns_validated_schema():
    agent = RequirementAnalystAgent(MockLLMProvider())
    result = agent.analyze("Add JWT authentication. Create login and registration endpoints.")
    assert isinstance(result, RequirementAnalysis)
    assert result.task
    assert result.requirements
