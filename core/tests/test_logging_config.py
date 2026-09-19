import io
import logging

from core.observability.logging_config import JsonFormatter, get_logger, parse_log_line


def _capture(logger_name: str, log_fn_name: str, message: str, **extra) -> dict:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())

    logger = logging.getLogger(logger_name)
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    getattr(logger, log_fn_name)(message, extra=extra)
    return parse_log_line(stream.getvalue().strip())


def test_log_line_is_valid_json_with_base_fields():
    record = _capture("test.logger.a", "info", "something happened")
    assert record["level"] == "INFO"
    assert record["logger"] == "test.logger.a"
    assert record["message"] == "something happened"
    assert "timestamp" in record


def test_extra_fields_are_included_in_the_json():
    record = _capture("test.logger.b", "info", "tool ran", tool_name="git.commit", duration_ms=12.5)
    assert record["tool_name"] == "git.commit"
    assert record["duration_ms"] == 12.5


def test_exception_info_is_included_when_logged():
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("test.logger.c")
    logger.handlers = [handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    try:
        raise ValueError("boom")
    except ValueError:
        logger.exception("it broke")

    record = parse_log_line(stream.getvalue().strip())
    assert "ValueError" in record["exception"]
    assert "boom" in record["exception"]


def test_get_logger_returns_a_standard_logger_instance():
    logger = get_logger("forgeai.something")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "forgeai.something"
