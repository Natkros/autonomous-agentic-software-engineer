import os

from code_intelligence.graph.dependency_graph import build_import_graph
from code_intelligence.indexing.repository_scanner import RepositoryScanner

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), "fixtures", "sample_repo")


def test_import_graph_resolves_internal_python_imports():
    index = RepositoryScanner().scan(FIXTURE_ROOT)
    all_paths = [f.path for f in index.files]
    graph = build_import_graph(index.imports, all_paths)

    assert "app/models/user.py" in graph.edges["app/services/auth_service.py"]
    assert "app/services/auth_service.py" in graph.edges["app/main.py"]


def test_import_graph_importers_of_reverse_lookup():
    index = RepositoryScanner().scan(FIXTURE_ROOT)
    all_paths = [f.path for f in index.files]
    graph = build_import_graph(index.imports, all_paths)

    importers = graph.importers_of("app/models/user.py")
    assert "app/services/auth_service.py" in importers


def test_import_graph_treats_unresolved_modules_as_external():
    index = RepositoryScanner().scan(FIXTURE_ROOT)
    all_paths = [f.path for f in index.files]
    graph = build_import_graph(index.imports, all_paths)

    assert "fastapi" in graph.external["app/main.py"]
