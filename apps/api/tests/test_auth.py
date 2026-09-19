def test_register_creates_user(client):
    response = client.post(
        "/api/auth/register", json={"email": "new@forgeai.dev", "password": "supersecret1"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new@forgeai.dev"
    assert body["role"] == "DEVELOPER"
    assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client):
    payload = {"email": "dup@forgeai.dev", "password": "supersecret1"}
    first = client.post("/api/auth/register", json=payload)
    second = client.post("/api/auth/register", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409


def test_login_with_valid_credentials_returns_token(client):
    client.post("/api/auth/register", json={"email": "login@forgeai.dev", "password": "supersecret1"})
    response = client.post(
        "/api/auth/login", data={"username": "login@forgeai.dev", "password": "supersecret1"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 0


def test_login_with_invalid_password_rejected(client):
    client.post("/api/auth/register", json={"email": "bad@forgeai.dev", "password": "supersecret1"})
    response = client.post(
        "/api/auth/login", data={"username": "bad@forgeai.dev", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_unauthenticated_request_is_rejected(client):
    response = client.get("/api/repositories")
    assert response.status_code == 401
