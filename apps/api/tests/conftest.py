import os
import shutil
import subprocess
import tempfile

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-secret")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_SAMPLE_REPO_SOURCE = os.path.join(_REPO_ROOT, "code_intelligence", "tests", "fixtures", "sample_repo")

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_engine():
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def local_git_repo():
    """A real, throwaway git repository on disk (an actual `git init` +
    commit, not a mock), so the /analyze endpoint's `git clone` can be
    exercised end-to-end without any network access.
    """
    workdir = tempfile.mkdtemp(prefix="forgeai-test-repo-")
    repo_path = os.path.join(workdir, "sample_repo")
    shutil.copytree(_SAMPLE_REPO_SOURCE, repo_path)

    env = {**os.environ, "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
           "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com"}
    subprocess.run(["git", "init", "-q"], cwd=repo_path, check=True, env=env)
    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "fixture commit"], cwd=repo_path, check=True, env=env)

    yield repo_path
    shutil.rmtree(workdir, ignore_errors=True)


@pytest.fixture()
def registered_user_token(client):
    client.post("/api/auth/register", json={"email": "dev@forgeai.dev", "password": "supersecret1"})
    response = client.post(
        "/api/auth/login",
        data={"username": "dev@forgeai.dev", "password": "supersecret1"},
    )
    return response.json()["access_token"]
