import os

from code_intelligence.indexing.repository_scanner import RepositoryScanner
from code_intelligence.retrieval.hybrid_search import HybridRetriever

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), "fixtures", "sample_repo")


def _retriever():
    index = RepositoryScanner().scan(FIXTURE_ROOT)
    return HybridRetriever(index)


def test_symbol_search_finds_exact_symbol_by_name():
    retriever = _retriever()
    results = retriever.search("authenticate_user")
    top_files = {r.chunk.file_path for r in results[:3]}
    assert "app/services/auth_service.py" in top_files
    top = results[0]
    assert top.chunk.symbol_name.endswith("authenticate_user")
    assert "symbol" in top.matched_signals


def test_path_search_finds_matches_by_file_path_fragment():
    retriever = _retriever()
    results = retriever.search("auth_service")
    assert any(r.chunk.file_path == "app/services/auth_service.py" for r in results)


def test_keyword_search_finds_docstring_matches():
    retriever = _retriever()
    results = retriever.search("session payload")
    assert any(r.chunk.symbol_name.endswith("authenticate_user") for r in results)


def test_search_over_empty_index_returns_no_results():
    from code_intelligence.indexing.models import RepositoryIndex
    retriever = HybridRetriever(RepositoryIndex(root="."))
    assert retriever.search("anything") == []


def test_natural_language_query_surfaces_authentication_code():
    """Mirrors the project's own design example: 'find all code responsible
    for user authentication' should surface the auth service, not unrelated
    code like the Button component or ApiClient.
    """
    retriever = _retriever()
    results = retriever.search("find code responsible for user authentication")
    top_paths = [r.chunk.file_path for r in results[:3]]
    assert "app/services/auth_service.py" in top_paths
