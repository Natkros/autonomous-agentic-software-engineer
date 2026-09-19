"""Dispatch symbol extraction to the right language-specific extractor."""
from __future__ import annotations

from code_intelligence.ast_tools import javascript_extractor, python_extractor, typescript_heuristic
from code_intelligence.ast_tools.symbols import ImportRecord, Symbol

# Languages with a real, structural AST-based extractor.
AST_BACKED_LANGUAGES = {"python", "javascript"}
# Languages supported only via a documented best-effort heuristic.
HEURISTIC_LANGUAGES = {"typescript"}
SUPPORTED_LANGUAGES = AST_BACKED_LANGUAGES | HEURISTIC_LANGUAGES


class UnsupportedLanguageError(ValueError):
    pass


def extract_symbols(source: str, file_path: str, language: str) -> tuple[list[Symbol], list[ImportRecord]]:
    if language == "python":
        return python_extractor.extract_symbols(source, file_path)
    if language == "javascript":
        return javascript_extractor.extract_symbols(source, file_path)
    if language == "typescript":
        return typescript_heuristic.extract_symbols(source, file_path)
    raise UnsupportedLanguageError(language)
