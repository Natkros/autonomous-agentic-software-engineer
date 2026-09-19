import os

import pytest

from agents.repository.repository_agent import RepositoryExplorerAgent
from core.state.schemas import RepositorySummary

FIXTURE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "code_intelligence", "tests", "fixtures", "sample_repo",
))


def test_explore_returns_validated_summary_matching_scanner_facts():
    agent = RepositoryExplorerAgent()
    summary = agent.explore(FIXTURE_ROOT)

    assert isinstance(summary, RepositorySummary)
    assert summary.file_count > 0
    assert "FastAPI" in summary.frameworks
    assert "python" in summary.languages
    assert "javascript" in summary.languages
    assert "app/main.py" in summary.entry_points
    assert summary.test_file_count >= 1
    assert summary.symbol_count > 0


def test_key_files_prioritizes_entry_points_and_is_capped():
    agent = RepositoryExplorerAgent()
    summary = agent.explore(FIXTURE_ROOT)

    assert summary.key_files[0] == "app/main.py"
    assert len(summary.key_files) <= 10


def test_explore_raises_for_missing_directory():
    agent = RepositoryExplorerAgent()
    with pytest.raises(NotADirectoryError):
        agent.explore("/definitely/does/not/exist")
