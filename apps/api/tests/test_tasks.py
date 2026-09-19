def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_repository(client, token, url):
    return client.post(
        "/api/repositories",
        json={"name": "task-repo", "url": url},
        headers=auth_headers(token),
    ).json()


def test_create_task_runs_full_pipeline_against_real_repository(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)

    response = client.post(
        "/api/tasks",
        json={"repository_id": repository["id"], "user_request": "Add a health check endpoint."},
        headers=auth_headers(registered_user_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["errors"] is None
    assert body["requirement_analysis"]["task"] == "Add a health check endpoint."
    assert "FastAPI" in body["repository_summary"]["frameworks"]
    assert len(body["plan"]) >= 1
    assert len(body["patch_proposals"]) >= 1


def test_create_task_default_autonomy_awaits_approval_and_writes_nothing(client, registered_user_token, local_git_repo):
    """Default `autonomy_level` (1, LEVEL_1_SUGGESTIONS) must review the
    proposals but apply nothing — matching `core/tests/test_execution_node.py`'s
    direct test of the same behavior, exercised here through the real API.
    """
    repository = _create_repository(client, registered_user_token, local_git_repo)

    response = client.post(
        "/api/tasks",
        json={"repository_id": repository["id"], "user_request": "Add a health check endpoint."},
        headers=auth_headers(registered_user_token),
    )

    body = response.json()
    assert body["autonomy_level"] == 1
    assert body["execution_status"] == "AWAITING_APPROVAL"
    assert len(body["review_results"]) >= 1
    assert len(body["approval_requests"]) == 1
    assert body["correction_results"] is None or body["correction_results"] == []
    assert body["git_commit"] is None


def test_create_task_full_autonomy_applies_tests_and_commits_for_real(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)

    response = client.post(
        "/api/tasks",
        json={
            "repository_id": repository["id"],
            "user_request": "Add a health check endpoint. Do not break existing routes.",
            "autonomy_level": 5,
        },
        headers=auth_headers(registered_user_token),
    )

    body = response.json()
    assert body["autonomy_level"] == 5
    assert body["execution_status"] == "COMPLETED", body["errors"]
    assert len(body["correction_results"]) >= 1
    assert body["correction_results"][0]["status"] == "success"
    assert body["git_commit"] is not None
    assert body["git_commit"]["sha"]


def test_create_task_records_failure_for_unclonable_repository(client, registered_user_token):
    repository = _create_repository(client, registered_user_token, "https://example.invalid/nonexistent.git")

    response = client.post(
        "/api/tasks",
        json={"repository_id": repository["id"], "user_request": "Add a feature"},
        headers=auth_headers(registered_user_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["errors"]


def test_create_task_requires_repository_ownership(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)

    client.post("/api/auth/register", json={"email": "other-task@forgeai.dev", "password": "supersecret1"})
    other_token = client.post(
        "/api/auth/login", data={"username": "other-task@forgeai.dev", "password": "supersecret1"}
    ).json()["access_token"]

    response = client.post(
        "/api/tasks",
        json={"repository_id": repository["id"], "user_request": "Add a feature"},
        headers=auth_headers(other_token),
    )
    assert response.status_code == 404


def test_get_task_returns_the_stored_run(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)
    created = client.post(
        "/api/tasks",
        json={"repository_id": repository["id"], "user_request": "Add a health check endpoint."},
        headers=auth_headers(registered_user_token),
    ).json()

    response = client.get(f"/api/tasks/{created['id']}", headers=auth_headers(registered_user_token))
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_task_not_found(client, registered_user_token):
    response = client.get("/api/tasks/does-not-exist", headers=auth_headers(registered_user_token))
    assert response.status_code == 404


def test_get_task_requires_ownership(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)
    created = client.post(
        "/api/tasks",
        json={"repository_id": repository["id"], "user_request": "Add a health check endpoint."},
        headers=auth_headers(registered_user_token),
    ).json()

    client.post("/api/auth/register", json={"email": "other-get-task@forgeai.dev", "password": "supersecret1"})
    other_token = client.post(
        "/api/auth/login", data={"username": "other-get-task@forgeai.dev", "password": "supersecret1"}
    ).json()["access_token"]

    response = client.get(f"/api/tasks/{created['id']}", headers=auth_headers(other_token))
    assert response.status_code == 404
