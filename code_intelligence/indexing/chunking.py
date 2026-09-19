"""Turn extracted symbols into embeddable text chunks.

One chunk per top-level function/class (methods are nested inside their
class's chunk source text isn't re-sliced here since we don't keep full file
contents in the index — the chunk text is a compact, embeddable summary
rather than a byte-exact source slice).
"""
from __future__ import annotations

from dataclasses import dataclass

from code_intelligence.ast_tools.symbols import Symbol


@dataclass
class CodeChunk:
    chunk_id: str
    text: str
    file_path: str
    symbol_name: str
    kind: str
    lineno: int

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "text": self.text,
            "file_path": self.file_path,
            "symbol_name": self.symbol_name,
            "kind": self.kind,
            "lineno": self.lineno,
        }


def build_chunks(symbols: list[Symbol]) -> list[CodeChunk]:
    chunks: list[CodeChunk] = []
    for sym in symbols:
        if sym.kind == "import":
            continue
        parts = [f"{sym.kind} {sym.qualified_name()}", f"file: {sym.file_path}"]
        if sym.bases:
            parts.append(f"extends: {', '.join(sym.bases)}")
        if sym.decorators:
            parts.append(f"decorators: {', '.join(sym.decorators)}")
        if sym.docstring:
            parts.append(sym.docstring.strip())
        text = "\n".join(parts)
        chunk_id = f"{sym.file_path}:{sym.lineno}:{sym.qualified_name()}"
        chunks.append(CodeChunk(
            chunk_id=chunk_id, text=text, file_path=sym.file_path,
            symbol_name=sym.qualified_name(), kind=sym.kind, lineno=sym.lineno,
        ))
    return chunks
