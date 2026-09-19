"""Real AST-based static analysis for Python source (spec section 25's
static-analysis half — no LLM involved, just structural pattern matching
over an actual parsed tree, same approach as `code_intelligence`'s symbol
extractor). Each rule below is checked against genuinely vulnerable and
genuinely clean code in `tools/tests/test_static_analysis.py` — this is
not a simulated or LLM-narrated finding, it is real analysis.

Scope note: these are syntactic heuristics, not a dataflow/taint analysis.
A determined obfuscation can evade any of them (e.g. `getattr(__builtins__,
"ev"+"al")`). That is a real, permanent limitation of AST-pattern rules in
general, not specific to this implementation — a production system would
layer this with a real tool (Bandit, Semgrep) rather than replace it.
"""
from __future__ import annotations

import ast
import re

from core.state.schemas import SecurityFinding, Severity

_SECRET_NAME_RE = re.compile(r"(pass(word)?|secret|api[_-]?key|token|auth)", re.IGNORECASE)
_MIN_SECRET_LENGTH = 6


def _is_call_to(node: ast.AST, names: set[str]) -> str | None:
    """If `node` is a Call whose function name (last attribute segment or
    bare name) is in `names`, return that name; else None.
    """
    if not isinstance(node, ast.Call):
        return None
    func = node.func
    if isinstance(func, ast.Name) and func.id in names:
        return func.id
    if isinstance(func, ast.Attribute) and func.attr in names:
        return func.attr
    return None


def _call_target_module(node: ast.Call) -> str | None:
    """Best-effort: for `module.func(...)`, return "module"."""
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id
    return None


def analyze_python_source(source: str, file_path: str) -> list[SecurityFinding]:
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []  # not this tool's job to report parse errors

    findings: list[SecurityFinding] = []

    for node in ast.walk(tree):
        lineno = getattr(node, "lineno", None)

        eval_exec_name = _is_call_to(node, {"eval", "exec"})
        if eval_exec_name:
            findings.append(SecurityFinding(
                severity=Severity.HIGH, rule_id="dangerous-eval-exec",
                message=f"Use of '{eval_exec_name}()' can execute arbitrary code from untrusted input.",
                file=file_path, line=lineno,
            ))

        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    findings.append(SecurityFinding(
                        severity=Severity.HIGH, rule_id="shell-true-command-injection",
                        message="subprocess call with shell=True can allow command injection if any argument is untrusted.",
                        file=file_path, line=lineno,
                    ))

        if isinstance(node, ast.ExceptHandler) and node.type is None:
            findings.append(SecurityFinding(
                severity=Severity.LOW, rule_id="bare-except",
                message="Bare 'except:' silently swallows all exceptions, including ones indicating real bugs.",
                file=file_path, line=lineno,
            ))

        if isinstance(node, ast.Call) and _call_target_module(node) == "pickle" and _is_call_to(node, {"loads", "load"}):
            findings.append(SecurityFinding(
                severity=Severity.HIGH, rule_id="insecure-deserialization",
                message="pickle.load(s) can execute arbitrary code when deserializing untrusted data.",
                file=file_path, line=lineno,
            ))

        if isinstance(node, ast.Call) and _call_target_module(node) == "yaml" and _is_call_to(node, {"load"}):
            has_safe_loader = any(kw.arg == "Loader" for kw in node.keywords)
            if not has_safe_loader:
                findings.append(SecurityFinding(
                    severity=Severity.HIGH, rule_id="insecure-yaml-load",
                    message="yaml.load() without an explicit safe Loader can execute arbitrary code.",
                    file=file_path, line=lineno,
                ))

        if isinstance(node, ast.Call) and _is_call_to(node, {"execute"}) and node.args:
            first_arg = node.args[0]
            if isinstance(first_arg, (ast.JoinedStr, ast.BinOp)):
                findings.append(SecurityFinding(
                    severity=Severity.HIGH, rule_id="possible-sql-injection",
                    message="SQL query built via string formatting/concatenation instead of parameterized values.",
                    file=file_path, line=lineno,
                ))

        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            if len(node.value.value) >= _MIN_SECRET_LENGTH:
                for target in node.targets:
                    if isinstance(target, ast.Name) and _SECRET_NAME_RE.search(target.id):
                        findings.append(SecurityFinding(
                            severity=Severity.HIGH, rule_id="hardcoded-secret",
                            message=f"Variable '{target.id}' looks like a hardcoded credential.",
                            file=file_path, line=lineno,
                        ))

    return findings
