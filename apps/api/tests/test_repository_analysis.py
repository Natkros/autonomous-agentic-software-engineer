def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_repository(client, token, url):
    return client.post(
        "/api/repositories",
        json={"name": "analyzed-repo", "url": url},
        headers=auth_headers(token),
    ).json()


def test_analyze_clones_and_scans_a_real_repository(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)

    response = client.post(
        f"/api/repositories/{repository['id']}/analyze",
        headers=auth_headers(registered_user_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["error_message"] is None

    summary = body["summary"]
    assert summary["file_count"] > 0
    assert "FastAPI" in summary["frameworks"]
    symbol_names = {s["qualified_name"] for s in summary["symbols"]}
    assert "AuthService.authenticate_user" in symbol_names


def test_analyze_records_failure_for_unclonable_url(client, registered_user_token):
    repository = _create_repository(client, registered_user_token, "https://example.invalid/nonexistent.git")

    response = client.post(
        f"/api/repositories/{repository['id']}/analyze",
        headers=auth_headers(registered_user_token),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "FAILED"
    assert body["summary"] is None
    assert body["error_message"]


def test_get_analysis_returns_404_before_any_run(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)

    response = client.get(
        f"/api/repositories/{repository['id']}/analysis",
        headers=auth_headers(registered_user_token),
    )
    assert response.status_code == 404


def test_get_analysis_returns_the_latest_run(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)
    client.post(f"/api/repositories/{repository['id']}/analyze", headers=auth_headers(registered_user_token))

    response = client.get(
        f"/api/repositories/{repository['id']}/analysis",
        headers=auth_headers(registered_user_token),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"


def test_analyze_requires_ownership(client, registered_user_token, local_git_repo):
    repository = _create_repository(client, registered_user_token, local_git_repo)

    client.post("/api/auth/register", json={"email": "other@forgeai.dev", "password": "supersecret1"})
    other_token = client.post(
        "/api/auth/login", data={"username": "other@forgeai.dev", "password": "supersecret1"}
    ).json()["access_token"]

    response = client.post(
        f"/api/repositories/{repository['id']}/analyze",
        headers=auth_headers(other_token),
    )
    assert response.status_code == 404
