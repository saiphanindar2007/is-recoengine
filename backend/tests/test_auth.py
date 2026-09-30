def test_register_creates_account_and_returns_token(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Officer One", "email": "officer1@example.gov.in",
        "password": "Officer1Pass", "role": "OFFICER",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["role"] == "OFFICER"
    assert "access_token" in body


def test_register_rejects_weak_password(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Weak Pw", "email": "weak@example.gov.in",
        "password": "onlylowercase", "role": "OFFICER",
    })
    assert resp.status_code == 422  # no digit


def test_register_duplicate_email_rejected(client):
    payload = {"full_name": "Dup", "email": "dup@example.gov.in", "password": "DupPass1", "role": "OFFICER"}
    first = client.post("/api/auth/register", json=payload)
    assert first.status_code == 200
    second = client.post("/api/auth/register", json=payload)
    assert second.status_code == 400


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json={
        "full_name": "Login Test", "email": "logintest@example.gov.in",
        "password": "CorrectPass1", "role": "OFFICER",
    })
    resp = client.post("/api/auth/login", json={"email": "logintest@example.gov.in", "password": "WrongPass1"})
    assert resp.status_code == 401


def test_me_requires_valid_token(client):
    resp = client.get("/api/auth/me")
    assert resp.status_code == 401
    resp2 = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp2.status_code == 401


def test_logout_revokes_token(client, register_and_login, auth_header):
    token = register_and_login(client, "logout1@example.gov.in", "LogoutPass1", "OFFICER")
    ok = client.get("/api/auth/me", headers=auth_header(token))
    assert ok.status_code == 200

    logout_resp = client.post("/api/auth/logout", headers=auth_header(token))
    assert logout_resp.status_code == 200

    after_logout = client.get("/api/auth/me", headers=auth_header(token))
    assert after_logout.status_code == 401
