from pydantic import BaseModel

from core.policies.permissions import AutonomyLevel, PermissionLevel
from tools.base import AuditLog, Tool, ToolRegistry


class _DoubleParams(BaseModel):
    value: int


class _DoubleTool(Tool):
    name = "test.double"
    description = "Doubles a number. Test-only tool."
    permission = PermissionLevel.EXECUTION
    input_schema = _DoubleParams

    def _execute(self, params: _DoubleParams) -> dict:
        return {"doubled": params.value * 2}


class _AlwaysFailsTool(Tool):
    name = "test.always_fails"
    description = "Always raises. Test-only tool."
    permission = PermissionLevel.READ_ONLY
    input_schema = _DoubleParams

    def _execute(self, params: _DoubleParams) -> dict:
        raise RuntimeError("boom")


def test_tool_runs_successfully_within_permission():
    audit_log = AuditLog()
    result = _DoubleTool().run(audit_log, AutonomyLevel.LEVEL_3_AUTO_TEST_AND_DEBUG, value=21)
    assert result.success is True
    assert result.output == {"doubled": 42}
    assert len(audit_log) == 1
    assert audit_log.to_list()[0]["success"] is True


def test_tool_denied_when_autonomy_level_too_low():
    audit_log = AuditLog()
    result = _DoubleTool().run(audit_log, AutonomyLevel.LEVEL_0_READ_ONLY, value=21)
    assert result.success is False
    assert "requires permission" in result.error
    assert len(audit_log) == 1
    assert audit_log.to_list()[0]["success"] is False


def test_tool_failure_is_caught_and_audited_not_raised():
    audit_log = AuditLog()
    result = _AlwaysFailsTool().run(audit_log, AutonomyLevel.LEVEL_5_FULL_AUTONOMY, value=1)
    assert result.success is False
    assert "boom" in result.error
    assert len(audit_log) == 1


def test_tool_registry_register_get_and_list():
    registry = ToolRegistry()
    tool = _DoubleTool()
    registry.register(tool)

    assert registry.get("test.double") is tool
    assert registry.list_tools() == [tool]


def test_tool_registry_rejects_duplicate_names():
    registry = ToolRegistry()
    registry.register(_DoubleTool())
    try:
        registry.register(_DoubleTool())
        assert False, "expected ValueError for duplicate tool name"
    except ValueError:
        pass


def test_tool_registry_raises_for_unknown_name():
    registry = ToolRegistry()
    try:
        registry.get("does.not.exist")
        assert False, "expected KeyError"
    except KeyError:
        pass
