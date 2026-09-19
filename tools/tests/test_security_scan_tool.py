import os
import tempfile

from core.policies.permissions import AutonomyLevel
from tools.base import AuditLog
from tools.security.security_scan_tool import SecurityScanTool

# Assembled via concatenation, not a contiguous literal, so this fixture
# file's own source text never contains a real-looking secret verbatim —
# see the note in test_secret_scanner.py for why that matters.
_FAKE_AWS_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"


def test_scans_every_file_in_workspace_and_aggregates_findings():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "app.py"), "w") as fh:
            fh.write("eval(x)\n")
        with open(os.path.join(root, ".env"), "w") as fh:
            fh.write(f"AWS_KEY = '{_FAKE_AWS_KEY}'\n")
        with open(os.path.join(root, "clean.py"), "w") as fh:
            fh.write("def add(a, b):\n    return a + b\n")

        result = SecurityScanTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=root)

    assert result.success is True
    rule_ids = {f["rule_id"] for f in result.output["findings"]}
    assert "dangerous-eval-exec" in rule_ids
    assert "aws-access-key-id" in rule_ids
    assert result.output["blocks_finalization"] is True


def test_clean_workspace_does_not_block_finalization():
    with tempfile.TemporaryDirectory() as root:
        with open(os.path.join(root, "clean.py"), "w") as fh:
            fh.write("def add(a, b):\n    return a + b\n")

        result = SecurityScanTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=root)

    assert result.output["findings"] == []
    assert result.output["blocks_finalization"] is False


def test_skips_ignored_directories():
    with tempfile.TemporaryDirectory() as root:
        os.makedirs(os.path.join(root, "node_modules"))
        with open(os.path.join(root, "node_modules", "bad.py"), "w") as fh:
            fh.write("eval(x)\n")

        result = SecurityScanTool().run(AuditLog(), AutonomyLevel.LEVEL_0_READ_ONLY, workspace_root=root)

    assert result.output["findings"] == []
