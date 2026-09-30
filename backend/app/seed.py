"""
Seeds the database with the curated Indian Standards corpus and (by default)
one demo account per role, so every role's UI can be exercised immediately
after deploy.

SECURITY NOTE: the demo OFFICER/AUDITOR accounts use well-known,
publicly-documented passwords. This is intentional and fine for a
hackathon/demo deployment, but must NOT be relied on for a real production
rollout. Two safety valves are provided, and the admin one is enforced, not
just documented:

  1. Set SEED_DEMO_ACCOUNTS=false to skip creating the OFFICER/AUDITOR demo
     accounts entirely.
  2. Set ADMIN_BOOTSTRAP_EMAIL / ADMIN_BOOTSTRAP_PASSWORD to real credentials.
     When APP_ENV=production, ADMIN_BOOTSTRAP_PASSWORD is REQUIRED — seeding
     hard-fails at import time rather than silently falling back to the
     well-known default admin@isreco.gov.in / Admin@123, which a previous
     version did unconditionally regardless of SEED_DEMO_ACCOUNTS. render.yaml
     sets this automatically via Render's random-value generation, so a
     fresh free-tier Render deploy is safe with zero manual steps.

Run once: `python -m app.seed` (idempotent — safe to re-run; existing
accounts and standards already in the DB are left untouched).
"""
import json
import os
import datetime as dt
from pathlib import Path

from . import models, auth
from .database import SessionLocal, engine, Base

SEED_FILE = Path(__file__).resolve().parent / "seed_standards.json"

SEED_DEMO_ACCOUNTS = os.environ.get("SEED_DEMO_ACCOUNTS", "true").lower() != "false"
APP_ENV = os.environ.get("APP_ENV", "development")

ADMIN_EMAIL = os.environ.get("ADMIN_BOOTSTRAP_EMAIL", "admin@isreco.gov.in")
ADMIN_PASSWORD = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "Admin@123")
_ADMIN_IS_DEFAULT = "ADMIN_BOOTSTRAP_PASSWORD" not in os.environ

# SECURITY: the previous version's two "safety valves" (SEED_DEMO_ACCOUNTS /
# ADMIN_BOOTSTRAP_PASSWORD) were both opt-in — an operator who deployed
# without reading this file's docstring got a live production instance with
# a publicly-documented admin@isreco.gov.in / Admin@123 login, since the
# ADMIN account was seeded unconditionally regardless of SEED_DEMO_ACCOUNTS.
# This is now a hard, fail-loud gate instead of an opt-in one: seeding
# simply refuses to create/leave a known-default admin password when
# APP_ENV=production. render.yaml pairs with this by generating a real
# random ADMIN_BOOTSTRAP_PASSWORD value at deploy time, so a fresh Render
# deploy never has to think about this — it just works and is already safe.
if APP_ENV == "production" and _ADMIN_IS_DEFAULT:
    raise RuntimeError(
        "Refusing to seed the database: APP_ENV=production but ADMIN_BOOTSTRAP_PASSWORD "
        "is not set, so the well-known default admin password (documented in this repo's "
        "README) would otherwise be used. Set ADMIN_BOOTSTRAP_EMAIL and "
        "ADMIN_BOOTSTRAP_PASSWORD to real values before seeding a production instance."
    )

DEMO_USERS = [
    dict(full_name="Ananya Rao", email=ADMIN_EMAIL, password=ADMIN_PASSWORD,
         role="ADMIN", department="Bureau of Indian Standards", designation="Standards Custodian"),
]
if SEED_DEMO_ACCOUNTS:
    DEMO_USERS += [
        dict(full_name="Vikram Sundaram", email="officer@isreco.gov.in", password="Officer@123",
             role="OFFICER", department="Central Public Works Department", designation="Procurement Officer"),
        dict(full_name="Meera Iyer", email="auditor@isreco.gov.in", password="Auditor@123",
             role="AUDITOR", department="Department of Consumer Affairs", designation="Compliance Auditor"),
    ]


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        for u in DEMO_USERS:
            existing = db.query(models.User).filter(models.User.email == u["email"]).first()
            if existing:
                continue
            user = models.User(
                full_name=u["full_name"],
                email=u["email"],
                hashed_password=auth.hash_password(u["password"]),
                role=u["role"],
                department=u["department"],
                designation=u["designation"],
            )
            db.add(user)
        db.commit()

        admin = db.query(models.User).filter(models.User.email == ADMIN_EMAIL).first()

        with open(SEED_FILE, "r", encoding="utf-8") as f:
            standards = json.load(f)

        DEMO_SUPERSEDED = {
            "IS 302 (Part 2/Sec 3):1994": "IS 302 (Part 1):2008",
        }

        added = 0
        for s in standards:
            existing = db.query(models.Standard).filter(models.Standard.is_number == s["is_number"]).first()
            if existing:
                continue
            is_number = s["is_number"]
            std = models.Standard(
                is_number=is_number,
                title=s["title"],
                category=s.get("category", "Uncategorised"),
                scope=s.get("scope", ""),
                latest_version=s.get("latest_version", ""),
                amendments=s.get("amendments", []),
                allied_standards=s.get("allied_standards", []),
                normative_references=s.get("normative_references", []),
                certification=s.get("certification", []),
                keywords=s.get("keywords", []),
                status="PUBLISHED",
                is_current=is_number not in DEMO_SUPERSEDED,
                superseded_by=DEMO_SUPERSEDED.get(is_number),
                created_by_id=admin.id if admin else None,
                # Seed data is curated from the public BIS catalogue/search
                # portal at seed time, not machine-scraped live — recorded
                # honestly as the source, with a verification timestamp so
                # the "unverified data" warning doesn't fire for every demo
                # standard on a fresh deploy.
                source_reference="BIS Standards Catalogue (bis.gov.in) — manually curated at seed time, "
                                  "not a live feed. Re-verify against bis.gov.in before citing in a live tender.",
                last_verified_at=dt.datetime.now(dt.UTC),
                verified_by_id=admin.id if admin else None,
            )
            db.add(std)
            added += 1
        db.commit()

        print(f"Seed complete. Standards added this run: {added}.")
        print("Accounts ready:")
        for u in DEMO_USERS:
            label = " (DEFAULT — CHANGE FOR PRODUCTION)" if u["email"] == ADMIN_EMAIL and _ADMIN_IS_DEFAULT else ""
            print(f"   {u['role']:8s} -> {u['email']} / {u['password']}{label}")
        if not SEED_DEMO_ACCOUNTS:
            print("SEED_DEMO_ACCOUNTS=false — officer/auditor demo accounts were skipped. "
                  "Use 'Manage Users' as the admin above to create real accounts.")
        if _ADMIN_IS_DEFAULT:
            print("WARNING: using the default admin bootstrap password. Set ADMIN_BOOTSTRAP_EMAIL "
                  "and ADMIN_BOOTSTRAP_PASSWORD env vars before deploying to production.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
