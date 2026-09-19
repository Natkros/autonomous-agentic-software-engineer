"""File-level classification: language, test files, config files, entry points."""
from __future__ import annotations

import os

EXTENSION_LANGUAGE = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".c": "c",
    ".cs": "csharp",
    ".php": "php",
    ".sql": "sql",
    ".sh": "shell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".toml": "toml",
    ".md": "markdown",
    ".html": "html",
    ".css": "css",
}

CONFIG_FILENAMES = {
    "package.json", "pyproject.toml", "requirements.txt", "requirements-dev.txt",
    "setup.py", "setup.cfg", "poetry.lock", "package-lock.json", "yarn.lock",
    "pnpm-lock.yaml", "docker-compose.yml", "docker-compose.yaml", "Dockerfile",
    ".env", ".env.example", "tsconfig.json", "next.config.js", "next.config.mjs",
    "tailwind.config.ts", "tailwind.config.js", "pytest.ini", "jest.config.js",
    "alembic.ini", "Makefile", ".gitignore", "go.mod", "Cargo.toml", "Gemfile",
}

ENTRY_POINT_CANDIDATES = {
    "main.py", "app.py", "manage.py", "wsgi.py", "asgi.py",
    "index.js", "index.ts", "server.js", "server.ts",
    "main.go", "main.rs",
}

TEST_FILENAME_MARKERS = ("test_", "_test", ".test.", ".spec.")
TEST_DIR_MARKERS = ("test", "tests", "__tests__", "spec")

IGNORED_DIR_NAMES = {
    ".git", "node_modules", "__pycache__", ".venv", "venv", ".next",
    "dist", "build", ".pytest_cache", ".mypy_cache", "coverage", ".idea", ".vscode",
}


def detect_language(path: str) -> str:
    _, ext = os.path.splitext(path)
    return EXTENSION_LANGUAGE.get(ext.lower(), "unknown")


def is_config_file(path: str) -> bool:
    return os.path.basename(path) in CONFIG_FILENAMES


def is_entry_point(path: str) -> bool:
    return os.path.basename(path) in ENTRY_POINT_CANDIDATES


def is_test_file(path: str) -> bool:
    name = os.path.basename(path).lower()
    if any(marker in name for marker in TEST_FILENAME_MARKERS):
        return True
    parts = {p.lower() for p in path.replace("\\", "/").split("/")}
    return bool(parts & set(TEST_DIR_MARKERS))


def should_ignore_dir(dirname: str) -> bool:
    return dirname in IGNORED_DIR_NAMES
