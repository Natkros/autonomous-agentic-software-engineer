"""Verifies classification against REAL Python failures, not crafted
strings — each test writes an actually-broken test file, actually runs
pytest against it via LocalProcessSandbox, and classifies the genuine
captured output. No fixtures are hand-faked here.
"""
import os
import tempfile

from agents.debugger.failure_classifier import classify_failure
from core.policies.permissions import AutonomyLevel
from core.state.schemas import FailureCategory
from sandbox.local_process_sandbox import LocalProcessSandbox
from tools.base import AuditLog
from tools.testing.run_tests_tool import RunTestsTool


def _run_and_classify(root: str, filename: str, content: str) -> FailureCategory:
    with open(os.path.join(root, filename), "w") as fh:
        fh.write(content)
    result = RunTestsTool(sandbox=LocalProcessSandbox()).run(
        AuditLog(), AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG, workspace_root=root,
    )
    return classify_failure(result.output["stdout"], result.output["stderr"], result.output["timed_out"])


def test_classifies_a_real_import_error():
    with tempfile.TemporaryDirectory() as root:
        category = _run_and_classify(
            root, "test_broken.py",
            "import this_module_definitely_does_not_exist_xyz\n\ndef test_x():\n    pass\n",
        )
    assert category == FailureCategory.IMPORT_ERROR


def test_classifies_a_real_type_error():
    with tempfile.TemporaryDirectory() as root:
        category = _run_and_classify(
            root, "test_broken.py",
            "def test_x():\n    1 + 'a'\n",
        )
    assert category == FailureCategory.TYPE_ERROR


def test_classifies_a_real_assertion_failure_as_test_error():
    with tempfile.TemporaryDirectory() as root:
        category = _run_and_classify(
            root, "test_broken.py",
            "def test_x():\n    assert 1 == 2\n",
        )
    assert category == FailureCategory.TEST_ERROR


def test_classifies_a_real_syntax_error():
    with tempfile.TemporaryDirectory() as root:
        category = _run_and_classify(
            root, "test_broken.py",
            "def test_x(:\n    pass\n",
        )
    assert category == FailureCategory.SYNTAX_ERROR


def test_classifies_no_tests_collected_as_config_error():
    with tempfile.TemporaryDirectory() as root:
        category = _run_and_classify(root, "not_a_test_file.py", "x = 1\n")
    assert category == FailureCategory.CONFIG_ERROR


def test_classifies_timeout_directly_without_needing_output():
    assert classify_failure(stdout="", stderr="", timed_out=True) == FailureCategory.TIMEOUT


def test_classifies_empty_output_as_unknown():
    assert classify_failure(stdout="", stderr="", timed_out=False) == FailureCategory.UNKNOWN
