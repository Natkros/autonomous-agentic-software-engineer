def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_repository(client, registered_user_token):
    create_response = client.post(
        "/api/repositories",
        json={"name": "forgeai-demo", "url": "https://github.com/example/forgeai-demo"},
        headers=auth_headers(registered_user_token),
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["name"] == "forgeai-demo"

    list_response = client.get("/api/repositories", headers=auth_headers(registered_user_token))
    assert list_response.status_code == 200
    repos = list_response.json()
    assert len(repos) == 1
    assert repos[0]["id"] == created["id"]


def test_get_repository_not_found(client, registered_user_token):
    response = client.get("/api/repositories/does-not-exist", headers=auth_headers(registered_user_token))
    assert response.status_code == 404


def test_repository_isolated_per_owner(client):
    client.post("/api/auth/register", json={"email": "a@forgeai.dev", "password": "supersecret1"})
    client.post("/api/auth/register", json={"email": "b@forgeai.dev", "password": "supersecret1"})

    token_a = client.post(
        "/api/auth/login", data={"username": "a@forgeai.dev", "password": "supersecret1"}
    ).json()["access_token"]
    token_b = client.post(
        "/api/auth/login", data={"username": "b@forgeai.dev", "password": "supersecret1"}
    ).json()["access_token"]

    created = client.post(
        "/api/repositories",
        json={"name": "owned-by-a", "url": "https://github.com/example/owned-by-a"},
        headers=auth_headers(token_a),
    ).json()

    other_view = client.get(f"/api/repositories/{created['id']}", headers=auth_headers(token_b))
    assert other_view.status_code == 404

    b_list = client.get("/api/repositories", headers=auth_headers(token_b))
    assert b_list.json() == []
