import pytest

from code_intelligence.ast_tools.python_extractor import PythonExtractionError, extract_symbols

SOURCE = '''
import os
from app.database import Base


class User(Base):
    """A registered user."""

    def full_name(self) -> str:
        return "x"


@app.get("/health")
def health_check():
    return {"status": "ok"}
'''


def test_extracts_class_and_bases():
    symbols, _ = extract_symbols(SOURCE, "app/models/user.py")
    classes = [s for s in symbols if s.kind == "class"]
    assert len(classes) == 1
    assert classes[0].name == "User"
    assert classes[0].bases == ["Base"]
    assert classes[0].docstring == "A registered user."


def test_extracts_nested_method_with_parent():
    symbols, _ = extract_symbols(SOURCE, "app/models/user.py")
    methods = [s for s in symbols if s.kind == "method"]
    assert len(methods) == 1
    assert methods[0].name == "full_name"
    assert methods[0].parent == "User"
    assert methods[0].qualified_name() == "User.full_name"


def test_extracts_top_level_function_with_decorator():
    symbols, _ = extract_symbols(SOURCE, "app/main.py")
    functions = [s for s in symbols if s.kind == "function"]
    assert len(functions) == 1
    assert functions[0].name == "health_check"
    assert functions[0].decorators == ["app.get"]


def test_extracts_imports():
    _, imports = extract_symbols(SOURCE, "app/models/user.py")
    modules = {i.module for i in imports}
    assert "os" in modules
    assert "app.database" in modules
    from_import = next(i for i in imports if i.module == "app.database")
    assert from_import.names == ["Base"]
    assert from_import.is_relative is False


def test_invalid_python_raises_extraction_error():
    with pytest.raises(PythonExtractionError):
        extract_symbols("def broken(:\n", "broken.py")
