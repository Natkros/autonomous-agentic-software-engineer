from agents.reviewer.review_agent import CodeReviewAgent
from core.state.schemas import PatchOperation, PatchProposal, ReviewResult


def _proposal(content: str | None, file: str = "app/main.py") -> PatchProposal:
    return PatchProposal(
        task_id="TASK-001", file=file, operation=PatchOperation.INSERT,
        description="test change", rationale="test", content=content,
    )


def test_review_returns_info_finding_for_description_only_proposal():
    result = CodeReviewAgent().review(_proposal(content=None))
    assert isinstance(result, ReviewResult)
    assert result.approved is True
    assert result.findings[0].category == "review"


def test_review_flags_stub_implementations_from_mock_llm_provider():
    stub_content = '\n\ndef handle_add_login():\n    """Auto-generated stub for: add login"""\n    pass\n'
    result = CodeReviewAgent().review(_proposal(content=stub_content))
    assert any(f.rule_id == "stub-implementation" for f in result.findings)
    assert result.approved is True  # LOW severity does not block


def test_review_flags_real_security_issues_in_proposed_content():
    dangerous_content = "\n\ndef handler():\n    eval(user_input)\n"
    result = CodeReviewAgent().review(_proposal(content=dangerous_content))
    assert result.approved is False
    assert any(f.rule_id == "dangerous-eval-exec" for f in result.findings)


def test_review_flags_hardcoded_secrets_in_proposed_content():
    # Concatenated, not a contiguous literal, so this file's own source
    # never contains a real-looking secret verbatim (see test_secret_scanner.py).
    content = '\n\napi_key = "sk_live_' + '1234567890abcdef"\n'
    result = CodeReviewAgent().review(_proposal(content=content))
    assert result.approved is False


def test_review_of_non_python_file_only_runs_secret_scan():
    result = CodeReviewAgent().review(_proposal(content="body { color: red; }", file="app/style.css"))
    assert result.approved is True
    assert result.findings == []


def test_clean_python_content_is_approved_with_no_findings():
    content = "\n\ndef add(a, b):\n    return a + b\n"
    result = CodeReviewAgent().review(_proposal(content=content))
    assert result.approved is True
    assert result.findings == []
