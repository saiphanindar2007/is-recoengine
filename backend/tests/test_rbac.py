def test_officer_cannot_create_standard(client, register_and_login, auth_header):
    token = register_and_login(client, "officer_rbac@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post("/api/standards", json={
        "is_number": "IS 9001:2024", "title": "x", "category": "x", "scope": "x",
    }, headers=auth_header(token))
    assert resp.status_code == 403


def test_auditor_cannot_create_standard(client, register_and_login, auth_header):
    token = register_and_login(client, "auditor_rbac@example.gov.in", "AuditorPass1", "AUDITOR")
    resp = client.post("/api/standards", json={
        "is_number": "IS 9002:2024", "title": "x", "category": "x", "scope": "x",
    }, headers=auth_header(token))
    assert resp.status_code == 403


def test_admin_can_create_standard(client, register_and_login, auth_header):
    token = register_and_login(client, "admin_rbac@example.gov.in", "AdminPass1", "ADMIN")
    resp = client.post("/api/standards", json={
        "is_number": "IS 9003:2024", "title": "RBAC Test Standard", "category": "Test",
        "scope": "A standard used purely to test RBAC.",
    }, headers=auth_header(token))
    assert resp.status_code == 200


def test_officer_cannot_view_analytics(client, register_and_login, auth_header):
    token = register_and_login(client, "officer_analytics@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.get("/api/analytics/summary", headers=auth_header(token))
    assert resp.status_code == 403


def test_auditor_can_view_analytics(client, register_and_login, auth_header):
    token = register_and_login(client, "auditor_analytics@example.gov.in", "AuditorPass1", "AUDITOR")
    resp = client.get("/api/analytics/summary", headers=auth_header(token))
    assert resp.status_code == 200


def test_officer_cannot_deactivate_users(client, register_and_login, auth_header):
    admin_token = register_and_login(client, "admin_deact@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "officer_deact_target@example.gov.in", "OfficerPass1", "OFFICER")
    me = client.get("/api/auth/me", headers=auth_header(officer_token)).json()

    officer_actor_token = register_and_login(client, "officer_deact_actor@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.put(f"/api/users/{me['id']}/deactivate", headers=auth_header(officer_actor_token))
    assert resp.status_code == 403

    # admin CAN do it
    resp2 = client.put(f"/api/users/{me['id']}/deactivate", headers=auth_header(admin_token))
    assert resp2.status_code == 200
    assert resp2.json()["is_active"] is False
