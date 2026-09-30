# IS-RecoEngine — Enterprise Edition
### AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications
**Smart India Hackathon — PS 26108** · Ministry of Consumer Affairs, Food & Public Distribution (DoCA)

![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
_(Replace `OWNER/REPO` above with this repo's actual GitHub path once pushed — GitHub fills in the badge automatically.)_

A full-stack, role-based, multi-page platform with a hybrid semantic search engine, explainable
recommendations, immutable audit logging, rate limiting, token revocation, automated tests, and
CI/CD — built to be free-tier deployable without giving up production-grade engineering practices.

## Roles

| Role | Who | What they can do |
|---|---|---|
| **OFFICER** — Procurement Officer | e.g. CPWD engineer | Search/recommend standards (text or uploaded tender document), build & save specification packages, flag standards as outdated |
| **ADMIN** — Standards Custodian | BIS / DoCA | Full CRUD on the catalogue, manage user accounts, resolve change requests, view the audit log |
| **AUDITOR** — Compliance Auditor | DoCA oversight | Read-only analytics dashboard + audit log — usage trends, most-recommended standards, open issues |

Demo accounts (seeded automatically):
```
ADMIN    admin@isreco.gov.in    / Admin@123
OFFICER  officer@isreco.gov.in  / Officer@123
AUDITOR  auditor@isreco.gov.in  / Auditor@123
```

## v4 update — "Must Fix Before SIH/Demo" priority tier

A structured audit (`Final Priority Matrix`) flagged 8 items as must-fix before demo. All 8 are
now implemented and covered by tests (38 total, up from 20):

1. **Registration role security** — public `/api/auth/register` is hard-locked to the OFFICER
   role (rejects any other role with a 400, not a silent downgrade). ADMIN/AUDITOR accounts can
   only be created by an existing ADMIN via `POST /api/users` — verified by test and live curl.
2. **Verify all tests** — full suite re-run clean after every change in this pass; 38/38 passing.
3. **Recommendation accuracy evaluation** — a real labelled dataset (`app/eval_dataset.py`, 18
   realistic procurement queries) with a metrics module (`app/evaluation.py`) computing Hit@K,
   Precision@K, MRR, NDCG@K, F1@K, exposed at `GET /api/analytics/evaluation` and in the
   Admin/Auditor dashboards. Real measured result on the seed corpus: **MRR 0.944, Hit@5 100%**
   (TF-IDF-only mode) — not a fabricated number, and a regression test asserts MRR ≥ 0.5 so future
   changes can't silently break matching quality.
4. **Low-confidence / no-match handling** — every recommendation response now carries an explicit
   `match_status` (`MATCHED` / `LOW_CONFIDENCE` / `NO_MATCH`) and human-readable `guidance`,
   surfaced as a banner in the UI instead of a bare empty list.
5. **Recommendation explainability** — `matched_terms` (already present) plus a new
   `score_breakdown` showing the TF-IDF and embedding components separately, so a result's score
   is never just an opaque number.
6. **Normative relationship correctness** — graph traversal rewritten to be depth-bounded and
   cycle-safe with an explicit `visited` set (a mutual-reference cycle A→B→A is covered by a
   dedicated test and cannot loop or duplicate).
7. **Document-processing reliability** — uploads are now validated by extension AND magic bytes
   (a renamed `.exe` claiming to be a `.pdf` is rejected), extraction runs under a hard 15s
   timeout, and the document is split into clauses (not blindly truncated to one excerpt) with
   each clause run through the recommendation pipeline separately and results aggregated —
   verified by a test with a real multi-clause tender document.
8. **Secure secrets/configuration** — production startup now refuses to boot with a wildcard CORS
   origin or the default JWT secret (verified via subprocess tests that actually launch the app
   with production env vars and assert it fails); the seed script's demo credentials are
   overridable via `ADMIN_BOOTSTRAP_EMAIL`/`ADMIN_BOOTSTRAP_PASSWORD` and skippable via
   `SEED_DEMO_ACCOUNTS=false` for a real deployment.

## v5 update — second "must fix" pass + UI polish

A second audit flagged 5 more P0s and a handful of deployment-config nits. All fixed, test suite
now **47/47 passing**, real CI (`.github/workflows/ci.yml`) runs it on every push:

1. **List-endpoint visibility bypass** — `GET /api/standards?status=DRAFT` let a non-admin see
   non-PUBLISHED standards (the PUBLISHED-only filter was only applied when no `status` param was
   given). Now unconditional for non-admins regardless of query params.
2. **Direct-fetch visibility bypass** — same class of bug via `GET /api/standards/{is_number}`,
   fixed the same way, plus a routing-order fix for the new `/verify` endpoint (see below).
3. **Default admin credentials on fresh deploy** — seeding now hard-fails at `APP_ENV=production`
   if `ADMIN_BOOTSTRAP_PASSWORD` isn't set, instead of silently falling back to a well-known
   default; `render.yaml` auto-generates it so a fresh Render deploy needs zero manual steps.
4. **Render blueprint fixes** — `env:` → `runtime:` (Render deprecated the old key), added the
   SPA rewrite route (`/* → /index.html`) the static frontend needs for client-side routing to
   survive a page refresh on any non-root path.
5. **`frontend/.env` was untracked-but-committable** — added a root `.gitignore` (env files,
   build output, local DBs, caches) so only `.env.example` is ever meant to be committed.
6. **Recommendation evidence** — every scored result now carries a HIGH/MEDIUM/LOW `confidence`
   label and a verbatim `evidence_snippet` quoted from the standard's own scope/title.
7. **Data provenance** — standards now carry `source_reference` / `last_verified_at` /
   `verified_by_id`, with an admin-only verify action that's invalidated automatically when the
   underlying content is edited, surfaced in the UI as a verified/unverified banner.
8. **Demo officer/auditor credentials also leaked into production** — found while cross-checking
   a deployment guide against the actual code: item 3 above closed the well-known-admin-password
   hole, but `SEED_DEMO_ACCOUNTS` (default `true`) was still unset in `render.yaml`, so a live
   deploy silently got `officer@isreco.gov.in`/`Officer@123` and `auditor@isreco.gov.in`/
   `Auditor@123` too. `render.yaml` now sets `SEED_DEMO_ACCOUNTS=false`. Also added the subprocess
   test for item 3's fail-loud behavior, which existed in code but had no test covering it
   (`test_production_seed_rejects_default_admin_password`).

## What's genuinely implemented (not roadmap prose)

- **Hybrid semantic search** — TF-IDF always on; a real sentence-transformer embedding layer
  activates automatically when `requirements-embeddings.txt` is installed, blending lexical and
  dense semantic similarity. Verified to degrade gracefully (logs a clear warning, keeps serving
  TF-IDF-only) when the model isn't installed — the service never fails to start over this.
- **Explainability** — every recommendation returns `matched_terms`, the actual query/document
  terms that drove the score, shown inline in the UI ("Why matched").
- **Full graph traversal** — allied *and* normative reference edges are both walked one hop out
  from every primary match, each tagged with which relation produced it. Covered by an
  integration test that forces the normative-only path (`test_recommend_expands_normative_references`).
- **Currency tracking** — standards can be marked `is_current=False` with a `superseded_by`
  pointer; search supports an `only_current` filter; the UI shows a "superseded" badge.
- **Multilingual query normalization** — Hindi/Tamil/Telugu term mapping with detected-script
  reporting, extensible to a full NMT service behind the same function signature.
- **Document upload** — `.pdf` / `.docx` / `.txt` tender documents can be uploaded directly;
  text is extracted and run through the same recommendation pipeline as typed queries.
- **Security hardening** — configurable CORS (no wildcard default), per-route rate limiting
  (slowapi), security response headers, enforced strong `JWT_SECRET_KEY` in production, server-side
  JWT revocation on logout (checked via `jti` on every request, not just client-side token deletion).
- **Immutable audit log** — every administrative mutation (standard CRUD, user activate/deactivate,
  change-request resolution) is recorded in an append-only `AuditLog` table with actor, action,
  target, and before/after detail. No endpoint anywhere updates or deletes these rows.
- **Automated tests** — 20 pytest tests covering auth, RBAC enforcement (403s verified, not
  assumed), dynamic index behavior (a created standard is searchable in the same test; a deleted
  one is not), the full officer→admin change-request workflow, and currency filtering. All 20 pass.
- **CI/CD** — GitHub Actions runs the backend test suite and a frontend production build on every
  push/PR (`.github/workflows/ci.yml`).
- **Dynamic index, always** — the semantic index rebuilds from the database on every standards
  create/update/delete. No static/frozen data path exists anywhere in the request flow.

## Architecture

```
backend/    FastAPI + SQLAlchemy + SQLite · JWT auth + revocation · role guards on every mutating
            endpoint · hybrid TF-IDF/embedding engine rebuilt live from the DB · rate limiting ·
            immutable audit log · pytest suite
frontend/   React 19 + Vite + Tailwind v4 + React Router — multi-page SPA, one UI per role,
            document upload, explainability chips, audit log viewer, Recharts analytics
```

## Run locally

**Backend**
```bash
cd backend
pip install -r requirements.txt
# optional, for real dense embeddings instead of TF-IDF-only (needs more RAM — see note below):
#   pip install -r requirements-embeddings.txt
cp .env.example .env   # edit as needed
python -m app.seed     # idempotent — creates demo accounts + loads the 43-standard corpus
uvicorn app.main:app --reload --port 8010
```

**Run the test suite**
```bash
cd backend
python -m pytest tests/ -v      # 20 tests, ~7s, no external services required
```

**Frontend** (separate terminal)
```bash
cd frontend
npm install
npm run dev               # http://localhost:5173, talks to http://localhost:8010 by default
```

Or everything at once: `docker compose up --build`

## Free-tier deployment

`render.yaml` deploys both services on Render's free tier. Push to GitHub → Render → New →
Blueprint → select the repo. After the backend deploys, update the frontend's `VITE_API_BASE` to
the backend's actual URL and redeploy.

**On the hybrid embedding layer and free tier**: `sentence-transformers` (+ PyTorch) is **not** in
the default `requirements.txt` because it can exceed what a 512MB free web service can build/run.
The default free-tier deploy runs TF-IDF-only — fully functional, just without the dense-embedding
signal. Installing `requirements-embeddings.txt` on a host with more RAM (a paid tier, or any
self-hosted/Docker environment ≥2GB RAM) activates hybrid semantic search automatically, with zero
code changes — `matching_engine.py` detects and uses it if present.

**On the database**: SQLite is used for zero-config free-tier deployability. Render's free web
services have an ephemeral filesystem, so the DB resets on redeploy — the seed script reruns
automatically every deploy. For persistent production data, set `DATABASE_URL` to a managed
Postgres instance (install `requirements-postgres.txt`) — no code changes needed.

## Honest scope note

Some things genuinely cannot be delivered without an external data-sharing agreement with BIS —
a live connection to the real ~22,000-standard BIS catalogue, a live amendment/notification feed,
and GeM/CPPP portal embedding all require institutional access no one outside BIS/DoCA can grant.
These are documented as roadmap items in `PROJECT_REPORT.md` rather than faked. Everything else —
search quality, security, testing, auditability, currency tracking, document ingestion — is real,
tested, and running in this codebase.

## Full documentation

See `PROJECT_REPORT.md` for the complete problem framing, architecture/methodology/flow diagrams,
novelty analysis, feasibility, risks, and references.
