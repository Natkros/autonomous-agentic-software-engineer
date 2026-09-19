from code_intelligence.ast_tools.symbols import Symbol
from code_intelligence.indexing.chunking import build_chunks


def test_build_chunks_skips_imports_and_includes_docstring():
    symbols = [
        Symbol(name="AuthService", kind="class", file_path="a.py", lineno=1, end_lineno=10, docstring="Handles auth."),
        Symbol(name="authenticate_user", kind="method", file_path="a.py", lineno=2, end_lineno=4, parent="AuthService", docstring="Verify credentials."),
    ]
    chunks = build_chunks(symbols)
    assert len(chunks) == 2
    method_chunk = next(c for c in chunks if c.symbol_name == "AuthService.authenticate_user")
    assert "Verify credentials." in method_chunk.text
    assert method_chunk.file_path == "a.py"
