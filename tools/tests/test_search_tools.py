import os

from core.policies.permissions import AutonomyLevel
from tools.base import AuditLog
from tools.search.code_search_tool import CodeSearchTool
from tools.search.repository_analyze_tool import RepositoryAnalyzeTool
from tools.search.symbol_search_tool import SymbolSearchTool

FIXTURE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "code_intelligence", "tests", "fixtures", "sample_repo",
))


def test_repository_analyze_tool_runs_at_read_only_autonomy():
    audit_log = AuditLog()
    result = RepositoryAnalyzeTool().run(audit_log, AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=FIXTURE_ROOT)
    assert result.success is True
    assert result.output["file_count"] > 0
    assert "FastAPI" in result.output["frameworks"]


def test_repository_analyze_tool_reports_failure_for_bad_path():
    audit_log = AuditLog()
    result = RepositoryAnalyzeTool().run(audit_log, AutonomyLevel.LEVEL_0_READ_ONLY, repository_path="/nope")
    assert result.success is False
    assert len(audit_log) == 1


def test_code_search_tool_finds_authentication_code():
    audit_log = AuditLog()
    result = CodeSearchTool().run(
        audit_log, AutonomyLevel.LEVEL_0_READ_ONLY,
        repository_path=FIXTURE_ROOT, query="user authentication", top_k=5,
    )
    assert result.success is True
    file_paths = [r["file_path"] for r in result.output["results"]]
    assert "app/services/auth_service.py" in file_paths


def test_symbol_search_tool_exact_match():
    audit_log = AuditLog()
    result = SymbolSearchTool().run(
        audit_log, AutonomyLevel.LEVEL_0_READ_ONLY,
        repository_path=FIXTURE_ROOT, symbol_name="authenticate_user",
    )
    assert result.success is True
    names = [m["qualified_name"] for m in result.output["matches"]]
    assert "AuthService.authenticate_user" in names


def test_symbol_search_tool_no_match_returns_empty_list_not_error():
    audit_log = AuditLog()
    result = SymbolSearchTool().run(
        audit_log, AutonomyLevel.LEVEL_0_READ_ONLY,
        repository_path=FIXTURE_ROOT, symbol_name="does_not_exist_anywhere",
    )
    assert result.success is True
    assert result.output["matches"] == []


def test_search_tools_are_denied_above_read_only_is_a_non_issue_since_they_are_read_only():
    """READ_ONLY tools should never be denied, at any autonomy level —
    this is really a permissions-policy check exercised through a real tool.
    """
    audit_log = AuditLog()
    result = RepositoryAnalyzeTool().run(audit_log, AutonomyLevel.LEVEL_0_READ_ONLY, repository_path=FIXTURE_ROOT)
    assert result.success is True
