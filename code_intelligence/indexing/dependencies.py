"""Parse dependency manifests and infer frameworks in use from them."""
from __future__ import annotations

import json
import re

from code_intelligence.indexing.models import Dependency

# Dependency name -> human-readable framework label.
FRAMEWORK_SIGNATURES = {
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "sqlalchemy": "SQLAlchemy",
    "pydantic": "Pydantic",
    "next": "Next.js",
    "react": "React",
    "vue": "Vue",
    "express": "Express",
    "@nestjs/core": "NestJS",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
}

_REQUIREMENT_LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9_.\-\[\]]+)\s*(==|>=|<=|~=|>|<)?\s*([\w.\-]*)"
)


def parse_requirements_txt(content: str, source_file: str) -> list[Dependency]:
    deps: list[Dependency] = []
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        match = _REQUIREMENT_LINE_RE.match(line)
        if not match:
            continue
        name = match.group(1).split("[")[0].strip()
        version = match.group(3).strip() or None
        if name:
            deps.append(Dependency(name=name.lower(), version=version, source_file=source_file, ecosystem="python"))
    return deps


def parse_package_json(content: str, source_file: str) -> list[Dependency]:
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return []
    deps: list[Dependency] = []
    for section in ("dependencies", "devDependencies"):
        for name, version in (data.get(section) or {}).items():
            deps.append(Dependency(name=name.lower(), version=version, source_file=source_file, ecosystem="javascript"))
    return deps


def parse_pyproject_toml(content: str, source_file: str) -> list[Dependency]:
    """Minimal best-effort extraction: pulls dependency-looking lines from a
    [tool.poetry.dependencies] / [project] style block without a full TOML
    parser dependency, since we only need dependency names for framework
    detection here, not a faithful re-serialization of the file.
    """
    deps: list[Dependency] = []
    in_deps_block = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("[") and line.endswith("]"):
            in_deps_block = "dependencies" in line
            continue
        if not in_deps_block or not line or line.startswith("#"):
            continue
        match = re.match(r'^"?([A-Za-z0-9_.\-]+)"?\s*=\s*"?([\w.\^~*]*)"?', line)
        if match and match.group(1).lower() != "python":
            deps.append(Dependency(
                name=match.group(1).lower(), version=match.group(2) or None,
                source_file=source_file, ecosystem="python",
            ))
    return deps


def detect_frameworks(dependencies: list[Dependency]) -> list[str]:
    names = {d.name for d in dependencies}
    frameworks = [label for key, label in FRAMEWORK_SIGNATURES.items() if key in names]
    return sorted(set(frameworks))
