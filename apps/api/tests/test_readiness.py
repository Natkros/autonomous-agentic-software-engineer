from app.database import get_db
from app.main import app


def test_ready_returns_200_when_database_is_reachable(client):
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_ready_returns_503_when_database_is_unreachable(client):
    class _UnreachableSession:
        def execute(self, *args, **kwargs):
            # A real broken connection fails when a query actually runs,
            # not when the session object itself is obtained - so that's
            # what this simulates, rather than making dependency
            # resolution itself raise (which FastAPI treats as a 500,
            # not something this endpoint's own try/except ever sees).
            raise ConnectionError("simulated: database unreachable")

    def unreachable_db():
        yield _UnreachableSession()

    app.dependency_overrides[get_db] = unreachable_db
    try:
        response = client.get("/api/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
    finally:
        del app.dependency_overrides[get_db]


def test_health_never_touches_the_database(client):
    def broken_db():
        raise ConnectionError("simulated: database unreachable")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = broken_db
    try:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    finally:
        del app.dependency_overrides[get_db]
