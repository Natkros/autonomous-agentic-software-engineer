from agents.coder.coding_agent import CodingAgent
from core.providers.llm_provider import MockLLMProvider
from core.state.schemas import PatchProposal, RepositorySummary, Task


def test_coding_agent_proposes_patch_for_task_with_explicit_file():
    agent = CodingAgent(MockLLMProvider())
    task = Task(id="TASK-001", description="Add a /health endpoint", files=["app/main.py"])
    summary = RepositorySummary(root="/tmp/repo", file_count=5, frameworks=["FastAPI"])

    proposal = agent.propose_patch(task, summary)

    assert isinstance(proposal, PatchProposal)
    assert proposal.task_id == "TASK-001"
    assert proposal.file == "app/main.py"


def test_coding_agent_falls_back_to_key_file_when_task_has_no_files():
    agent = CodingAgent(MockLLMProvider())
    task = Task(id="TASK-002", description="Add pagination")
    summary = RepositorySummary(root="/tmp/repo", file_count=5, key_files=["app/routes/users.py"])

    proposal = agent.propose_patch(task, summary)

    assert proposal.file == "app/routes/users.py"


def test_coding_agent_uses_unknown_when_no_files_available_anywhere():
    agent = CodingAgent(MockLLMProvider())
    task = Task(id="TASK-003", description="Add something")
    summary = RepositorySummary(root="/tmp/repo", file_count=0)

    proposal = agent.propose_patch(task, summary)

    assert proposal.file == "UNKNOWN"
