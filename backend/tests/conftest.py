"""
Test fixtures. Uses a throwaway SQLite file per test session (never the dev/
prod database) so tests are hermetic and safe to run in CI on every push.
"""
import os
import sys

os.environ["JWT_SECRET_KEY"] = "test-secret-key-not-for-production"
os.environ["DATABASE_URL"] = "sqlite:///./test_is_reco.db"
os.environ["EMBEDDING_MODE"] = "tfidf_only"  # deterministic, fast, no model download in CI
os.environ["CORS_ALLOWED_ORIGINS"] = "http://localhost:5173"
os.environ["RATE_LIMIT_ENABLED"] = "false"  # tests fire far more requests/sec than a real client would

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine, SessionLocal
from app.main import app
from app import matching_engine, models, auth as auth_module


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    db_path = "./test_is_reco.db"
    if os.path.exists(db_path):
        os.remove(db_path)


@pytest.fixture()
def client():
    return TestClient(app)


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


_BOOTSTRAP_ADMIN_EMAIL = "bootstrap-admin@example.gov.in"
_BOOTSTRAP_ADMIN_PASSWORD = "BootstrapAdmin1"
_bootstrap_token_cache = {"token": None}


def _bootstrap_admin_token(client) -> str:
    """Mirrors production reality: the very first ADMIN account cannot come
    from public self-registration (that's the whole point of the fix being
    tested) — it has to be created out-of-band, exactly like app/seed.py does
    for a real deployment. This creates that one bootstrap admin directly via
    the DB/password-hashing layer (not the HTTP API) once per test session,
    then every other account in the test suite is created through the real
    API using that admin's token, so the API surface itself stays fully
    exercised."""
    if _bootstrap_token_cache["token"]:
        return _bootstrap_token_cache["token"]

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.email == _BOOTSTRAP_ADMIN_EMAIL).first()
        if not existing:
            user = models.User(
                full_name="Bootstrap Admin",
                email=_BOOTSTRAP_ADMIN_EMAIL,
                hashed_password=auth_module.hash_password(_BOOTSTRAP_ADMIN_PASSWORD),
                role="ADMIN",
                department="Test", designation="Bootstrap",
            )
            db.add(user)
            db.commit()
    finally:
        db.close()

    resp = client.post("/api/auth/login", json={"email": _BOOTSTRAP_ADMIN_EMAIL, "password": _BOOTSTRAP_ADMIN_PASSWORD})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    _bootstrap_token_cache["token"] = token
    return token


def _register_and_login(client, email, password, role) -> str:
    """OFFICER accounts go through the real public /api/auth/register endpoint
    (exercising the self-service path). ADMIN/AUDITOR accounts go through the
    real POST /api/users endpoint, authenticated as the bootstrap admin —
    exercising the *actual* privileged-account-creation path rather than
    working around it."""
    role = role.upper()

    if role == "OFFICER":
        resp = client.post("/api/auth/register", json={
            "full_name": "Test User", "email": email, "password": password,
            "role": "OFFICER", "department": "Test Dept", "designation": "Tester",
        })
        if resp.status_code == 400:
            resp = client.post("/api/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return resp.json()["access_token"]

    admin_token = _bootstrap_admin_token(client)
    create_resp = client.post("/api/users", json={
        "full_name": "Test User", "email": email, "password": password,
        "role": role, "department": "Test Dept", "designation": "Tester",
    }, headers=_auth_header(admin_token))
    if create_resp.status_code == 400:
        pass  # already exists from an earlier test sharing this session-scoped DB
    else:
        assert create_resp.status_code == 200, create_resp.text

    login_resp = client.post("/api/auth/login", json={"email": email, "password": password})
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["access_token"]


@pytest.fixture()
def seeded_standard(client):
    """Creates one baseline standard as ADMIN and returns (admin_token, standard_payload).
    Idempotent: since the test DB is session-scoped, later tests requesting
    this fixture reuse the already-created standard rather than conflicting."""
    admin_token = _register_and_login(client, "seedadmin@example.gov.in", "AdminPass1", "ADMIN")
    payload = {
        "is_number": "IS 0001:2024",
        "title": "Test PVC Pipes for Potable Water Supply",
        "category": "Plastics & Pipes",
        "scope": "Specifies requirements for uPVC pipes used for potable cold water supply.",
        "latest_version": "First Revision, 2024",
        "amendments": [],
        "allied_standards": [],
        "normative_references": ["IS 0002:2024 Methods of test for uPVC pipes"],
        "certification": ["BIS Product Certification (ISI Mark) - Mandatory"],
        "keywords": ["pvc pipe", "water pipe", "plumbing"],
    }
    resp = client.post("/api/standards", json=payload, headers=_auth_header(admin_token))
    if resp.status_code == 400:
        pass  # already created by an earlier test sharing this session-scoped DB
    else:
        assert resp.status_code == 200, resp.text
    return admin_token, payload


@pytest.fixture()
def register_and_login():
    return _register_and_login


@pytest.fixture()
def auth_header():
    return _auth_header


@pytest.fixture()
def full_seed_corpus(client):
    """Loads the real 43-standard seed corpus (the same one app/seed.py loads
    for local/prod use) directly into the test DB, for tests that need to
    evaluate against realistic data rather than a handful of test-created
    standards. Idempotent — skips standards that already exist."""
    import json
    from pathlib import Path
    from app import models as app_models, matching_engine as me

    seed_file = Path(__file__).resolve().parent.parent / "app" / "seed_standards.json"
    with open(seed_file, "r", encoding="utf-8") as f:
        standards = json.load(f)

    db = SessionLocal()
    try:
        added = 0
        for s in standards:
            existing = db.query(app_models.Standard).filter(app_models.Standard.is_number == s["is_number"]).first()
            if existing:
                continue
            db.add(app_models.Standard(
                is_number=s["is_number"], title=s["title"], category=s.get("category", "Uncategorised"),
                scope=s.get("scope", ""), latest_version=s.get("latest_version", ""),
                amendments=s.get("amendments", []), allied_standards=s.get("allied_standards", []),
                normative_references=s.get("normative_references", []), certification=s.get("certification", []),
                keywords=s.get("keywords", []), status="PUBLISHED",
            ))
            added += 1
        db.commit()
        me.rebuild_index(db)
    finally:
        db.close()
    return added
