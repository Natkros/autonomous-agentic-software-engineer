from code_intelligence.parsers.language import (
    detect_language,
    is_config_file,
    is_entry_point,
    is_test_file,
    should_ignore_dir,
)


def test_detect_language_by_extension():
    assert detect_language("app/main.py") == "python"
    assert detect_language("frontend/lib/api.ts") == "typescript"
    assert detect_language("frontend/components/Button.jsx") == "javascript"
    assert detect_language("README.md") == "markdown"
    assert detect_language("data.bin") == "unknown"


def test_is_config_file():
    assert is_config_file("apps/api/requirements.txt")
    assert is_config_file("apps/web/package.json")
    assert not is_config_file("app/main.py")


def test_is_entry_point():
    assert is_entry_point("app/main.py")
    assert is_entry_point("some/dir/manage.py")
    assert not is_entry_point("app/services/auth_service.py")


def test_is_test_file():
    assert is_test_file("code_intelligence/tests/test_language.py")
    assert is_test_file("frontend/__tests__/button.test.tsx".replace("tsx", "js"))
    assert not is_test_file("app/services/auth_service.py")


def test_should_ignore_dir():
    assert should_ignore_dir("node_modules")
    assert should_ignore_dir(".git")
    assert not should_ignore_dir("app")
