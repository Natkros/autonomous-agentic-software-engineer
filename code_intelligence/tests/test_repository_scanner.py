import os

from code_intelligence.indexing.repository_scanner import RepositoryScanner

FIXTURE_ROOT = os.path.join(os.path.dirname(__file__), "fixtures", "sample_repo")


def _scan():
    return RepositoryScanner().scan(FIXTURE_ROOT)


def test_scan_raises_for_missing_directory():
    import pytest
    with pytest.raises(NotADirectoryError):
        RepositoryScanner().scan(os.path.join(FIXTURE_ROOT, "does-not-exist"))


def test_scan_discovers_files_and_ignores_nothing_irrelevant():
    index = _scan()
    paths = {f.path for f in index.files}
    assert "app/main.py" in paths
    assert "app/services/auth_service.py" in paths
    assert "frontend/components/Button.jsx" in paths
    assert "frontend/lib/api.ts" in paths


def test_scan_detects_dependencies_and_frameworks():
    index = _scan()
    dep_names = {d.name for d in index.dependencies}
    assert "fastapi" in dep_names
    assert "sqlalchemy" in dep_names
    assert "react" in dep_names
    assert "next" in dep_names
    assert "FastAPI" in index.frameworks
    assert "Next.js" in index.frameworks
    assert "React" in index.frameworks
    assert "SQLAlchemy" in index.frameworks


def test_scan_detects_entry_points_config_and_test_files():
    index = _scan()
    assert "app/main.py" in index.entry_points
    assert "requirements.txt" in index.config_files
    assert "package.json" in index.config_files
    assert any(f.endswith("test_auth.py") for f in index.test_files)


def test_scan_extracts_readme_summary():
    index = _scan()
    assert index.readme_summary is not None
    assert "fixture application" in index.readme_summary


def test_scan_detects_api_routes():
    index = _scan()
    methods = {(r["method"], r["handler"]) for r in index.api_routes}
    assert ("GET", "health_check") in methods
    assert ("POST", "login") in methods


def test_scan_detects_db_models():
    index = _scan()
    model_names = {m["name"] for m in index.db_models}
    assert "User" in model_names


def test_scan_extracts_symbols_across_languages():
    index = _scan()
    symbol_names = {s.qualified_name() for s in index.symbols}
    assert "AuthService.authenticate_user" in symbol_names  # Python
    assert "Button" in symbol_names  # JavaScript (JSX)
    assert "ApiClient" in symbol_names  # TypeScript heuristic
