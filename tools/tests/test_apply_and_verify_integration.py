"""End-to-end demonstration of the Phase 4 mechanism: apply a structured
patch to a real (copied) repository, then run its test suite to confirm
nothing broke — the "patch generation, test execution" capability the
roadmap calls for.

The patch content here is hand-written, not derived from
`MockLLMProvider` — Phase 3's mock produces placeholder text, not real
code, so using it here would demonstrate nothing. This test proves the
apply -> verify mechanism itself works on real files; wiring a real code
generator's output through it is future work (Phase 5+, or once a real
LLM provider is configured).
"""
import os
import shutil
import tempfile

from core.policies.permissions import AutonomyLevel
from core.state.schemas import PatchOperation
from sandbox.local_process_sandbox import LocalProcessSandbox
from tools.base import AuditLog
from tools.filesystem.patch_tool import FilesystemPatchTool
from tools.testing.run_tests_tool import RunTestsTool

FIXTURE_ROOT = os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "code_intelligence", "tests", "fixtures", "sample_repo",
))


def test_apply_a_safe_patch_then_confirm_existing_tests_still_pass():
    with tempfile.TemporaryDirectory() as workdir:
        workspace_root = os.path.join(workdir, "repo")
        shutil.copytree(FIXTURE_ROOT, workspace_root)
        audit_log = AuditLog()

        patch_result = FilesystemPatchTool().run(
            audit_log, AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES,
            workspace_root=workspace_root,
            path="app/services/auth_service.py",
            operation=PatchOperation.INSERT,
            content="\n    def revoke_session(self, email: str) -> dict:\n        return {\"email\": email, \"revoked\": True}\n",
        )
        assert patch_result.success is True

        with open(os.path.join(workspace_root, "app", "services", "auth_service.py")) as fh:
            assert "revoke_session" in fh.read()

        test_result = RunTestsTool(sandbox=LocalProcessSandbox()).run(
            audit_log, AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
            workspace_root=workspace_root, test_path="tests",
        )
        assert test_result.success is True
        assert test_result.output["all_passed"] is True

        # Both tool calls (patch + test run) must be in the same audit trail.
        tool_names = [record["tool_name"] for record in audit_log.to_list()]
        assert tool_names == ["filesystem.patch", "test.run"]


def test_a_syntax_breaking_patch_is_never_written_so_tests_still_pass_on_original_code():
    with tempfile.TemporaryDirectory() as workdir:
        workspace_root = os.path.join(workdir, "repo")
        shutil.copytree(FIXTURE_ROOT, workspace_root)
        audit_log = AuditLog()

        patch_result = FilesystemPatchTool().run(
            audit_log, AutonomyLevel.LEVEL_2_AUTO_CODE_CHANGES,
            workspace_root=workspace_root,
            path="app/services/auth_service.py",
            operation=PatchOperation.INSERT,
            content="\n    def broken(:\n",
        )
        assert patch_result.success is False

        test_result = RunTestsTool(sandbox=LocalProcessSandbox()).run(
            audit_log, AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
            workspace_root=workspace_root, test_path="tests",
        )
        assert test_result.output["all_passed"] is True
