import os
import tempfile

import pytest

from agents.security.security_agent import SecurityAgent, SecurityScanError
from core.state.schemas import SecurityScanResult


def test_scan_returns_validated_result_with_real_findings():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "app.py"), "w") as fh:
            fh.write("eval(user_input)\n")

        result = SecurityAgent().scan(root)

    assert isinstance(result, SecurityScanResult)
    assert result.blocks_finalization is True
    assert any(f.rule_id == "dangerous-eval-exec" for f in result.findings)


def test_scan_of_clean_repo_does_not_block():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "app.py"), "w") as fh:
            fh.write("def add(a, b):\n    return a + b\n")

        result = SecurityAgent().scan(root)

    assert result.blocks_finalization is False
    assert result.findings == []


def test_scan_raises_for_nonexistent_path():
    with pytest.raises(SecurityScanError):
        SecurityAgent().scan("/path/does/not/exist")
