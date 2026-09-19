import pytest

from code_intelligence.ast_tools.javascript_extractor import JavaScriptExtractionError, extract_symbols

JSX_SOURCE = '''
import React from "react";

export function Button({ label, onClick }) {
  return <button onClick={onClick}>{label}</button>;
}

export const IconButton = ({ icon }) => {
  return <button>{icon}</button>;
};
'''

CLASS_SOURCE = '''
class Base {}

class Repository extends Base {
  save() {}
  load() {}
}
'''


def test_extracts_function_declaration_from_export():
    symbols, _ = extract_symbols(JSX_SOURCE, "Button.jsx")
    functions = [s for s in symbols if s.kind == "function"]
    names = {s.name for s in functions}
    assert "Button" in names
    assert "IconButton" in names  # arrow function assigned to a const


def test_extracts_import():
    _, imports = extract_symbols(JSX_SOURCE, "Button.jsx")
    assert len(imports) == 1
    assert imports[0].module == "react"
    assert imports[0].names == ["React"]


def test_extracts_class_with_methods_and_base():
    symbols, _ = extract_symbols(CLASS_SOURCE, "repository.js")
    classes = [s for s in symbols if s.kind == "class"]
    repo = next(c for c in classes if c.name == "Repository")
    assert repo.bases == ["Base"]

    methods = [s for s in symbols if s.kind == "method" and s.parent == "Repository"]
    assert {m.name for m in methods} == {"save", "load"}


def test_invalid_javascript_raises_extraction_error():
    with pytest.raises(JavaScriptExtractionError):
        extract_symbols("function ( {{{ broken", "broken.js")
