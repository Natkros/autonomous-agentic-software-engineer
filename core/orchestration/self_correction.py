"""The bounded self-correction loop (spec section 21):

    CODE -> TEST -> PASS?
              |          \\
              | no        \\ yes
              v            v
        ANALYZE ERROR    (done)
              |
        IDENTIFY ROOT CAUSE
              |
            PATCH
              |
        TEST AGAIN  (up to `max_iterations` times total)

If `max_iterations` is exhausted without every test passing, the loop
stops and reports `NEEDS_HUMAN_INTERVENTION` — it never loops forever,
per the project's own hard rule ("Maximum autonomous iterations: 5").

This is a mechanism test, not a demonstration of AI code-fixing quality:
with `MockLLMProvider` (the only provider exercised in this environment),
the Coding Agent's patch content is a deterministic heuristic stub, not a
real fix informed by the failure. A patch that fails will therefore keep
failing the same way on every iteration, and the loop will correctly
exhaust its budget and hand off to a human — which is itself the
behavior this phase needs to prove works, independent of patch quality.
"""
from __future__ import annotations

from agents.coder.coding_agent import CodingAgent
from agents.debugger.debugger_agent import DebuggerAgent
from core.policies.permissions import AutonomyLevel
from core.providers.llm_provider import LLMProvider
from core.state.schemas import RepositorySummary, SelfCorrectionResult, SelfCorrectionStatus, Task
from tools.base import AuditLog
from tools.filesystem.patch_tool import FilesystemPatchTool
from tools.testing.run_tests_tool import RunTestsTool

DEFAULT_MAX_ITERATIONS = 5


def run_self_correction_loop(
    workspace_root: str,
    task: Task,
    repository_summary: RepositorySummary,
    llm_provider: LLMProvider,
    autonomy_level: AutonomyLevel = AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG,
    max_iterations: int = DEFAULT_MAX_ITERATIONS,
    test_path: str = ".",
) -> SelfCorrectionResult:
    coding_agent = CodingAgent(llm_provider)
    debugger_agent = DebuggerAgent(llm_provider)
    patch_tool = FilesystemPatchTool()
    test_tool = RunTestsTool()
    audit_log = AuditLog()

    debug_reports = []
    last_counts: dict = {}

    for iteration in range(1, max_iterations + 1):
        proposal = coding_agent.propose_patch(task, repository_summary)

        if proposal.content:
            patch_result = patch_tool.run(
                audit_log, autonomy_level,
                workspace_root=workspace_root, path=proposal.file,
                operation=proposal.operation, content=proposal.content,
            )
            if not patch_result.success:
                fake_output = {"stdout": "", "stderr": patch_result.error or "", "timed_out": False}
                debug_reports.append(debugger_agent.diagnose(fake_output, task, iteration=iteration))
                continue

        test_result = test_tool.run(audit_log, autonomy_level, workspace_root=workspace_root, test_path=test_path)
        output = test_result.output or {}
        last_counts = output.get("counts", {})

        if test_result.success and output.get("all_passed"):
            return SelfCorrectionResult(
                status=SelfCorrectionStatus.SUCCESS, iterations_used=iteration,
                debug_reports=debug_reports, final_test_counts=last_counts,
            )

        debug_reports.append(debugger_agent.diagnose(output, task, iteration=iteration))

    return SelfCorrectionResult(
        status=SelfCorrectionStatus.NEEDS_HUMAN_INTERVENTION, iterations_used=max_iterations,
        debug_reports=debug_reports, final_test_counts=last_counts,
    )
