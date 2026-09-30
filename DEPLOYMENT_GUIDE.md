# IS-RecoEngine — Full Implementation & Deployment Guide
### Local setup → GitHub → Free-Tier Deployment (Render)

This walks through the exact, verified commands for the v6 project — every command below has been
run against this codebase; nothing here is guessed.

---

## Part A — Local Implementation

### A.1 Prerequisites

| Tool | Version | Check |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| npm | 10+ | `npm --version` |
| git | any recent | `git --version` |

No database server, no Docker, and no paid API keys are required to run this locally.

### A.2 Unzip and orient yourself

```bash
unzip IS-RecoEngine-Enterprise-SIH26108.zip
cd is-reco-enterprise
ls
```

You should see:
```
backend/    frontend/    .github/    render.yaml    docker-compose.yml
README.md   PROJECT_REPORT.md   .gitignore
```

### A.3 Backend — install, configure, seed, run

```bash
cd backend

# 1. Install dependencies (lean, free-tier-safe set — no heavy ML deps)
pip install -r requirements.txt

# 2. Create your local environment file
cp .env.example .env
```

Open `.env` and leave the defaults as-is for local dev — they're already correct for `localhost`.
You do **not** need to change anything to run locally.

```bash
# 3. Seed the database (idempotent — safe to re-run)
python -m app.seed
```

Expected output:
```
Seed complete. Standards added this run: 43.
Accounts ready:
   ADMIN    -> admin@isreco.gov.in / Admin@123 (DEFAULT — CHANGE FOR PRODUCTION)
   OFFICER  -> officer@isreco.gov.in / Officer@123
   AUDITOR  -> auditor@isreco.gov.in / Auditor@123
WARNING: using the default admin bootstrap password. ...
```
That warning is expected and correct for local dev — `APP_ENV=development` by default, so the
default admin password is allowed. It becomes a hard error later once you deploy with
`APP_ENV=production` (see Part C) — that's intentional, not a bug.

```bash
# 4. Run the API
uvicorn app.main:app --reload --port 8010
```

Leave this running. In a **second terminal**, verify it's alive:
```bash
curl http://localhost:8010/api/health
# {"status":"ok","index_ready":true,"standards_indexed":43,"embeddings_active":false}
```

`embeddings_active: false` is expected and fine — the app runs on TF-IDF matching by default
(see §A.6 if you want the optional hybrid semantic layer).

### A.4 Backend — run the automated tests

In a terminal (can be the same one you seeded from, backend still running in the other):
```bash
cd backend
pytest tests/ -v
```
You should see all tests pass (47 at time of writing — run this command yourself for the exact
current count rather than trusting any number written in a doc, since the suite keeps growing).

### A.5 Frontend — install, configure, run

Open a **third terminal**:
```bash
cd frontend
npm install
cp .env.example .env
```
Edit `frontend/.env`:
```
VITE_API_BASE=http://localhost:8010
```
(This matches the port the backend is running on in §A.3.)

```bash
npm run dev
```
Open **http://localhost:5173** in a browser. Log in with any of the three seeded demo accounts
from §A.3. You should land on that role's dashboard (Officer → search/specifications, Admin →
catalogue management, Auditor → analytics).

### A.6 (Optional) Enable real hybrid semantic search locally

By default the matching engine runs TF-IDF-only — fast, lightweight, free-tier-safe. To also
activate dense sentence-embedding matching (better semantic understanding, e.g. matching "geyser"
to "water heater" with zero shared words):

```bash
cd backend
pip install -r requirements-embeddings.txt   # pulls in PyTorch — ~600MB-1GB, takes a few minutes
```
Nothing else to configure — `EMBEDDING_MODE=hybrid` is already the default in `.env.example`. Restart
`uvicorn`; the startup log will say `Dense embeddings active: True` and `/api/health` will confirm it.

### A.7 Sanity checklist before moving on

- [ ] `curl http://localhost:8010/api/health` returns `"status":"ok"`
- [ ] `pytest tests/ -v` — all green
- [ ] `npm run build` (inside `frontend/`) completes with no errors
- [ ] You can log in as all three demo roles in the browser and see distinct dashboards

If all four are true, the app is verified working end-to-end locally.

---

## Part B — Push to GitHub

### B.1 Initialize the repository

```bash
cd is-reco-enterprise      # the project root, containing backend/ frontend/ render.yaml etc.
git init
git add .
git status
```
Check the `git status` output: you should **not** see `frontend/node_modules`, `backend/__pycache__`,
any `*.db` file, or any `.env` (only `.env.example` files) staged. The included `.gitignore` already
excludes all of these — if you do see one of them listed, stop and check you're running `git add`
from the project root, not from inside `backend/` or `frontend/`.

```bash
git commit -m "Initial commit: IS-RecoEngine enterprise platform"
```

### B.2 Create the GitHub repository

1. Go to [github.com/new](https://github.com/new)
2. Repository name: `is-recoengine` (or anything you prefer)
3. **Do not** initialize with a README/`.gitignore`/license — you already have these locally, and
   adding them on GitHub too will create a merge conflict on first push
4. Create the repository, then copy the remote URL it shows you (HTTPS or SSH)

### B.3 Push

```bash
git remote add origin https://github.com/<your-username>/is-recoengine.git
git branch -M main
git push -u origin main
```

### B.4 Verify CI runs

Go to the **Actions** tab on your GitHub repo. You should see a workflow run start automatically
(`.github/workflows/ci.yml` triggers on every push to `main`). It runs:
- the full backend `pytest` suite
- `npm ci` + `npm run lint` + `npm run build` for the frontend

Wait for it to go green before deploying. If it fails, the logs will show exactly which step and
why — this is the same test/build you already ran locally in Part A, so a CI failure here usually
means something wasn't actually committed (check `git status` again) rather than a new bug.

---

## Part C — Free-Tier Deployment (Render)

This project ships a ready-to-use `render.yaml` **Blueprint** that deploys both services (API +
static frontend) in one step, with secrets auto-generated — you do not hand-configure environment
variables one by one.

### C.1 Create a Render account

Go to [render.com](https://render.com) and sign up (free tier requires no credit card for this
project's usage level — a web service + a static site, both on the free plan).

### C.2 Deploy via Blueprint

1. On the Render dashboard: **New** (top right) → **Blueprint**
2. Connect your GitHub account if you haven't already, and under **Connect a repository**, click
   **Connect** next to the `is-recoengine` repo you pushed in Part B
3. This opens a Blueprint creation form. Give it a **Blueprint Name**, confirm the **Branch** is
   `main`, and Render will show you the list of resources it's about to create by reading
   `render.yaml` — the two services described above
4. Click **Deploy Blueprint**

Render will now:
- Generate a random, strong `JWT_SECRET_KEY`
- Generate a random, strong `ADMIN_BOOTSTRAP_PASSWORD`
- Build the backend (`pip install -r requirements.txt`)
- Run `python -m app.seed` then start `uvicorn` (see the `startCommand` in `render.yaml`)
- Build the frontend (`npm install && npm run build`) and publish the `dist/` folder as a static site
- Apply the SPA rewrite rule (`/* → /index.html`) so client-side routes don't 404 on refresh

This takes a few minutes the first time. Watch the **Logs** tab on the `is-recoengine-api` service.

### C.3 Retrieve your real admin password

This is the one manual step, and it's deliberate — there's no known default password to leak.

1. On the `is-recoengine-api` service page, open **Logs**
2. Find the seed output, which looks like:
   ```
   Seed complete. Standards added this run: 43.
   Accounts ready:
      ADMIN    -> admin@isreco.gov.in / <a long random string>
   ```
3. Copy that password somewhere safe (a password manager). This is your real, only way to log in
   as the initial admin.

> Note: because `APP_ENV=production` is set in `render.yaml`, the app will **refuse to start** if
> this random password generation somehow didn't happen — this is the hard-fail security behavior
> verified in this project's test suite (`test_production_seed_rejects_default_admin_password`).
> If you ever see a boot failure mentioning `ADMIN_BOOTSTRAP_PASSWORD`, it means that env var is
> genuinely missing from the service's Environment tab — check it's still set to "Generate value."

### C.4 Confirm both services are live

- Backend health check: `https://is-recoengine-api.onrender.com/api/health` (or whatever URL
  Render assigned — check the service's top banner) should return
  `{"status":"ok","index_ready":true,"standards_indexed":43,...}`
- Frontend: open `https://is-recoengine-frontend.onrender.com` (again, check Render's actual
  assigned URL — it may differ slightly if that exact name was taken)

### C.5 If the two auto-generated URLs don't match what's hardcoded

`render.yaml` assumes the services will be named exactly `is-recoengine-api` and
`is-recoengine-frontend` (Render URLs are `https://<service-name>.onrender.com`). If Render had to
rename either one (e.g. because the name was already taken), two values need to be updated to
match the *actual* assigned URLs:

1. On `is-recoengine-api` → **Environment** tab → edit `CORS_ALLOWED_ORIGINS` to your actual
   frontend URL
2. On `is-recoengine-frontend` → **Environment** tab → edit `VITE_API_BASE` to your actual backend
   URL, then trigger a **Manual Deploy** on the frontend service (env var changes on a static site
   require a rebuild to take effect, since `VITE_API_BASE` gets baked into the JS bundle at build
   time)

### C.6 Log in and verify

1. Go to your frontend URL, click **Sign in**
2. Log in with `admin@isreco.gov.in` and the password from §C.3
3. You should land on the Admin dashboard. From here:
   - Go to **Manage Users** → **Create Staff Account** to create real Officer/Auditor accounts
     for actual users (`render.yaml` sets `SEED_DEMO_ACCOUNTS=false`, so no demo officer/auditor
     accounts exist on this deployment — everyone besides the initial ADMIN is created explicitly
     by you, the admin, which is the intended production posture)
   - Go to **Manage Standards** to confirm the 43-standard catalogue loaded correctly

### C.7 Free-tier behavior to know about

- **Cold starts**: Render's free web services spin down after ~15 minutes of inactivity and take
  ~30-60 seconds to wake up on the next request. This is a Render free-tier characteristic, not a
  bug in this project.
- **Ephemeral filesystem**: the SQLite database resets on every redeploy (this is why the seed
  script is baked into `startCommand` — it re-seeds automatically every time, and is idempotent so
  it won't duplicate data if the disk did happen to persist). If you need data to survive redeploys,
  see §C.8.
- **No custom domain on free tier** without upgrading — you get the `onrender.com` subdomain.

### C.8 (Optional) Upgrade to persistent PostgreSQL

Still achievable on free tiers (Render's free PostgreSQL, or Supabase's free tier):

1. Provision a free Postgres instance and copy its connection string
2. On `is-recoengine-api` → Environment → set `DATABASE_URL` to that connection string
3. Add `psycopg2-binary` to what gets installed — either merge `requirements-postgres.txt` into
   `requirements.txt`, or change the build command to
   `pip install -r requirements.txt -r requirements-postgres.txt`
4. Redeploy

No application code changes are needed — SQLAlchemy's `create_engine` already reads `DATABASE_URL`
generically.

---

## Part D — Post-Deployment Checklist

- [ ] `GET /api/health` on the live backend returns `"status":"ok"`
- [ ] Frontend loads and the login page renders correctly
- [ ] Login works with the real admin password retrieved from Render logs
- [ ] A direct link to a nested route (e.g. `https://your-frontend.onrender.com/officer/search`)
      loads correctly on a hard refresh — this specifically confirms the SPA rewrite rule is active
- [ ] Admin can create a new Officer/Auditor account via **Manage Users**
- [ ] A newly created Officer account can log in and run a search
- [ ] GitHub Actions CI is green on the `main` branch

---

## Part E — Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Frontend loads but API calls fail (network error in browser console) | `VITE_API_BASE` doesn't match the real backend URL | See §C.5 — update and **redeploy** the frontend (env changes on static sites need a rebuild) |
| Direct link to `/officer/search` 404s on refresh | SPA rewrite rule missing/not applied | Confirm the `routes:` block is present in `render.yaml` under the frontend service; redeploy |
| Backend won't boot, log mentions `JWT_SECRET_KEY` | `APP_ENV=production` but that var isn't set to a real value | Should be auto-generated by the Blueprint — check the Environment tab; regenerate if missing |
| Backend won't boot, log mentions `ADMIN_BOOTSTRAP_PASSWORD` | Same as above, different variable | Same fix — confirm it's set to "Generate value" in the service's Environment tab |
| `CORS` errors in the browser console | `CORS_ALLOWED_ORIGINS` on the backend doesn't include the frontend's actual origin | See §C.5 |
| Login works but returns to login page immediately | Browser blocking the auth token (rare, usually a stale cached build) | Hard-refresh / clear site data for the domain, try again |
| Local `pytest` fails on a test involving subprocess/production checks | Those tests spawn a real subprocess with production env vars — make sure nothing else in your shell has stray `APP_ENV`/`JWT_SECRET_KEY` values set that could interfere | Run in a clean terminal: `env -i PATH="$PATH" python3 -m pytest tests/ -v` |

---

## Quick Reference — All Commands in One Place

```bash
# ---- Local backend ----
cd backend
pip install -r requirements.txt
cp .env.example .env
python -m app.seed
uvicorn app.main:app --reload --port 8010
pytest tests/ -v                      # separate terminal

# ---- Local frontend ----
cd frontend
npm install
cp .env.example .env                  # set VITE_API_BASE=http://localhost:8010
npm run dev                           # http://localhost:5173
npm run build                         # production build check
npm run lint

# ---- GitHub ----
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<you>/is-recoengine.git
git branch -M main
git push -u origin main

# ---- Render (after connecting the repo via Blueprint in the dashboard) ----
# Nothing to run locally — Render builds from render.yaml automatically.
# Post-deploy, only manual step: copy the generated admin password from
# the is-recoengine-api service's Logs tab.
```
