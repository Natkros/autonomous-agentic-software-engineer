"""The Coding Agent — Phase 3 scope only.

It PROPOSES a patch (a structured, validated description of a change);
it does not touch the filesystem. Applying a patch requires the sandboxed
filesystem-write tools built in Phase 4 (SAFE_WRITE permission), which
don't exist yet. Keeping proposal and application separate also matches
the project's human-in-the-loop design: a proposal can be shown to a human
for approval before anything is ever written to disk.
"""
from __future__ import annotations

from core.providers.llm_provider import LLMProvider
from core.state.schemas import PatchProposal, RepositorySummary, Task

_SYSTEM_PROMPT = """You are a software engineer implementing one task from a larger plan.
Given the task and a summary of the repository, propose a single patch:
which file it touches, what kind of change it is, a description of the
change, and your rationale. You are NOT applying this change — only
proposing it for review. Respond only via the provided schema."""


class CodingAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider

    def propose_patch(self, task: Task, repository_summary: RepositorySummary) -> PatchProposal:
        candidate_file = task.files[0] if task.files else (
            repository_summary.key_files[0] if repository_summary.key_files else "UNKNOWN"
        )
        prompt = "\n".join([
            f"task_id: {task.id}",
            f"task: {task.description}",
            f"candidate_file: {candidate_file}",
            f"repository_frameworks: {', '.join(repository_summary.frameworks) or 'none detected'}",
        ])

        return self.llm_provider.generate_structured(
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=prompt,
            schema=PatchProposal,
        )
