from agents.debugger.debugger_agent import DebuggerAgent
from core.providers.llm_provider import MockLLMProvider
from core.state.schemas import DebugReport, FailureCategory, Task


def test_diagnose_uses_the_real_classifier_not_the_llm_layer():
    agent = DebuggerAgent(MockLLMProvider())
    task = Task(id="TASK-001", description="Add a health endpoint")
    test_output = {"stdout": "ModuleNotFoundError: No module named 'foo'", "stderr": "", "timed_out": False}

    report = agent.diagnose(test_output, task, iteration=2)

    assert isinstance(report, DebugReport)
    assert report.failure_category == FailureCategory.IMPORT_ERROR
    assert report.iteration == 2
    assert report.root_cause
    assert report.proposed_fix


def test_diagnose_classifies_timeout_correctly():
    agent = DebuggerAgent(MockLLMProvider())
    task = Task(id="TASK-001", description="Add a feature")
    test_output = {"stdout": "", "stderr": "", "timed_out": True}

    report = agent.diagnose(test_output, task)
    assert report.failure_category == FailureCategory.TIMEOUT


def test_diagnose_includes_output_excerpt_as_evidence():
    agent = DebuggerAgent(MockLLMProvider())
    task = Task(id="TASK-001", description="Add a feature")
    test_output = {"stdout": "AssertionError: expected 2 got 3", "stderr": "", "timed_out": False}

    report = agent.diagnose(test_output, task)
    assert "AssertionError" in report.evidence
