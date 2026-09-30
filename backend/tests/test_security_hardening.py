"""Tests for the P0 'Must Fix Before SIH/Demo' security items: registration
role-escalation lockdown, admin-only staff account creation, and production
CORS/secret enforcement."""
import subprocess
import sys
import os


def test_public_register_rejects_admin_role(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Attacker", "email": "attacker1@example.gov.in",
        "password": "AttackerPass1", "role": "ADMIN",
    })
    assert resp.status_code == 400
    assert "limited to Procurement Officer" in resp.json()["detail"]


def test_public_register_rejects_auditor_role(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Attacker2", "email": "attacker2@example.gov.in",
        "password": "AttackerPass1", "role": "AUDITOR",
    })
    assert resp.status_code == 400


def test_public_register_officer_still_works(client):
    resp = client.post("/api/auth/register", json={
        "full_name": "Legit Officer", "email": "legitofficer1@example.gov.in",
        "password": "LegitPass1", "role": "OFFICER",
    })
    assert resp.status_code == 200
    assert resp.json()["user"]["role"] == "OFFICER"


def test_admin_can_create_admin_and_auditor_accounts(client, register_and_login, auth_header):
    admin_token = register_and_login(client, "staffcreator@example.gov.in", "AdminPass1", "ADMIN")

    new_admin = client.post("/api/users", json={
        "full_name": "New Custodian", "email": "newcustodian1@example.gov.in",
        "password": "NewAdminPass1", "role": "ADMIN",
    }, headers=auth_header(admin_token))
    assert new_admin.status_code == 200
    assert new_admin.json()["role"] == "ADMIN"

    new_auditor = client.post("/api/users", json={
        "full_name": "New Auditor", "email": "newauditor1@example.gov.in",
        "password": "NewAuditorPass1", "role": "AUDITOR",
    }, headers=auth_header(admin_token))
    assert new_auditor.status_code == 200
    assert new_auditor.json()["role"] == "AUDITOR"


def test_officer_cannot_create_staff_accounts(client, register_and_login, auth_header):
    officer_token = register_and_login(client, "nonadmin_creator@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.post("/api/users", json={
        "full_name": "Sneaky", "email": "sneaky1@example.gov.in",
        "password": "SneakyPass1", "role": "ADMIN",
    }, headers=auth_header(officer_token))
    assert resp.status_code == 403


def test_officer_cannot_use_status_query_param_to_bypass_visibility(client, register_and_login, auth_header):
    """List-endpoint visibility check: a non-admin passing ?status=DRAFT (or
    any other non-PUBLISHED status) must still only ever see PUBLISHED
    standards. A previous version only forced the PUBLISHED filter when no
    `status` query param was supplied, so appending `?status=DRAFT` bypassed
    it entirely — the same class of visibility bug as the direct-fetch one,
    reachable through the list endpoint instead."""
    admin_token = register_and_login(client, "list_bypass_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "list_bypass_officer@example.gov.in", "OfficerPass1", "OFFICER")

    client.post("/api/standards", json={
        "is_number": "IS 6002:2026", "title": "Draft Standard Snoutwhistle",
        "category": "Test", "scope": "A draft that must not leak via list ?status= override.",
        "status": "DRAFT",
    }, headers=auth_header(admin_token))

    resp = client.get("/api/standards", params={"status": "DRAFT"}, headers=auth_header(officer_token))
    assert resp.status_code == 200
    numbers = [s["is_number"] for s in resp.json()]
    assert "IS 6002:2026" not in numbers
    assert all(s["status"] == "PUBLISHED" for s in resp.json())

    # ADMIN's status filter still works as intended.
    admin_resp = client.get("/api/standards", params={"status": "DRAFT"}, headers=auth_header(admin_token))
    admin_numbers = [s["is_number"] for s in admin_resp.json()]
    assert "IS 6002:2026" in admin_numbers


def test_officer_cannot_fetch_non_published_standard_directly(client, register_and_login, auth_header):
    """Direct-object-reference authorization check: GET /api/standards/{is_number}
    must enforce the same PUBLISHED-only visibility rule for non-admins that
    the list endpoint already enforces. A DRAFT standard should be invisible
    to an OFFICER even when its exact IS number is known/guessed."""
    admin_token = register_and_login(client, "draft_owner_admin@example.gov.in", "AdminPass1", "ADMIN")
    officer_token = register_and_login(client, "draft_viewer_officer@example.gov.in", "OfficerPass1", "OFFICER")

    create_resp = client.post("/api/standards", json={
        "is_number": "IS 6001:2026", "title": "Unpublished Draft Standard Wobblefinch",
        "category": "Test", "scope": "A draft standard that should not be readable by non-admins.",
        "status": "DRAFT",
    }, headers=auth_header(admin_token))
    assert create_resp.status_code in (200, 400)

    resp = client.get("/api/standards/IS 6001:2026", headers=auth_header(officer_token))
    assert resp.status_code == 404

    # ADMIN can still fetch it directly.
    admin_resp = client.get("/api/standards/IS 6001:2026", headers=auth_header(admin_token))
    assert admin_resp.status_code == 200
    assert admin_resp.json()["status"] == "DRAFT"


def test_admin_can_verify_standard_and_edit_clears_verification(client, register_and_login, auth_header, seeded_standard):
    admin_token, _ = seeded_standard

    verify_resp = client.put(
        "/api/standards/IS 0001:2024/verify",
        json={"source_reference": "BIS official gazette, checked manually.", "note": "Confirmed current."},
        headers=auth_header(admin_token),
    )
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["last_verified_at"] is not None
    assert body["source_reference"] == "BIS official gazette, checked manually."

    # Editing substantive content invalidates the prior verification.
    update_resp = client.put(
        "/api/standards/IS 0001:2024",
        json={"latest_version": "Second Revision, 2026"},
        headers=auth_header(admin_token),
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["last_verified_at"] is None


def test_officer_cannot_verify_standard(client, register_and_login, auth_header, seeded_standard):
    officer_token = register_and_login(client, "verify_officer@example.gov.in", "OfficerPass1", "OFFICER")
    resp = client.put(
        "/api/standards/IS 0001:2024/verify",
        json={"source_reference": "should not be allowed"},
        headers=auth_header(officer_token),
    )
    assert resp.status_code == 403


def test_production_seed_rejects_default_admin_password():
    """Runs a real subprocess importing app.seed with APP_ENV=production and no
    ADMIN_BOOTSTRAP_PASSWORD set, verifying seeding actually refuses to run
    with the well-known default admin password rather than just trusting the
    code path exists (same pattern as the CORS/JWT-secret subprocess checks
    above)."""
    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["JWT_SECRET_KEY"] = "a-sufficiently-long-random-production-secret-value"
    env["CORS_ALLOWED_ORIGINS"] = "https://example.com"
    env.pop("ADMIN_BOOTSTRAP_PASSWORD", None)  # force the well-known default
    env["DATABASE_URL"] = "sqlite:///./test_admin_seed_check.db"
    result = subprocess.run(
        [sys.executable, "-c", "import app.seed"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "ADMIN_BOOTSTRAP_PASSWORD" in result.stderr
    if os.path.exists("test_admin_seed_check.db"):
        os.remove("test_admin_seed_check.db")

    # And confirm it succeeds once a real bootstrap password is supplied.
    env["ADMIN_BOOTSTRAP_PASSWORD"] = "a-real-generated-production-password-1"
    result_ok = subprocess.run(
        [sys.executable, "-c", "import app.seed"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result_ok.returncode == 0
    if os.path.exists("test_admin_seed_check.db"):
        os.remove("test_admin_seed_check.db")
    """Runs a real subprocess importing app.main with APP_ENV=production and a
    wildcard CORS origin, verifying the app actually refuses to start rather
    than just trusting the code path exists."""
    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env["JWT_SECRET_KEY"] = "a-sufficiently-long-random-production-secret-value"
    env["CORS_ALLOWED_ORIGINS"] = "*"
    env["DATABASE_URL"] = "sqlite:///./test_cors_check.db"
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "CORS_ALLOWED_ORIGINS must not be" in result.stderr
    if os.path.exists("test_cors_check.db"):
        os.remove("test_cors_check.db")


def test_production_startup_rejects_default_jwt_secret():
    env = os.environ.copy()
    env["APP_ENV"] = "production"
    env.pop("JWT_SECRET_KEY", None)  # force the default dev secret
    env["DATABASE_URL"] = "sqlite:///./test_secret_check.db"
    result = subprocess.run(
        [sys.executable, "-c", "import app.main"],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode != 0
    assert "JWT_SECRET_KEY must be set" in result.stderr
    if os.path.exists("test_secret_check.db"):
        os.remove("test_secret_check.db")
