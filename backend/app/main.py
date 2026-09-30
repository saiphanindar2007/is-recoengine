import os
import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .rate_limit import limiter

from .database import Base, engine, SessionLocal, DB_URL
from . import matching_engine
from .routers import (
    auth_router, standards_router, recommend_router,
    specs_router, change_requests_router, analytics_router, users_router, audit_router,
)

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("is_reco.main")

Base.metadata.create_all(bind=engine)


def _sqlite_add_missing_columns():
    """`Base.metadata.create_all` only creates missing TABLES, not missing
    COLUMNS on a table that already exists — so an existing free-tier SQLite
    file from before this revision (which added `source_reference`,
    `last_verified_at`, `verified_by_id` to `standards`) would otherwise
    crash on first query. This is a best-effort, SQLite-only, additive-only
    patch (ADD COLUMN, never DROP/ALTER) so upgrading an already-deployed
    instance doesn't require manually recreating the database."""
    if not DB_URL.startswith("sqlite"):
        return
    needed = {
        "source_reference": "VARCHAR(500)",
        "last_verified_at": "DATETIME",
        "verified_by_id": "INTEGER",
    }
    with engine.connect() as conn:
        existing_cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(standards)").fetchall()}
        for col, coltype in needed.items():
            if col not in existing_cols:
                conn.exec_driver_sql(f"ALTER TABLE standards ADD COLUMN {col} {coltype}")
                logger.info(f"SQLite auto-migration: added missing column standards.{col}")


_sqlite_add_missing_columns()

app = FastAPI(
    title="IS-RecoEngine Enterprise API",
    description="Role-based AI recommendation engine for applicable Indian Standards "
                 "in procurement specifications — SIH PS 26108.",
    version="3.0.0",
)

# ---------------- Rate limiting (single shared instance, see rate_limit.py) ----------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---------------- CORS (configurable, not a wildcard by default in production) ----------------
_raw_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

_APP_ENV = os.environ.get("APP_ENV", "development")
if _APP_ENV == "production" and "*" in ALLOWED_ORIGINS:
    raise RuntimeError(
        "CORS_ALLOWED_ORIGINS must not be '*' when APP_ENV=production. "
        "Set it to the actual deployed frontend origin(s), comma-separated."
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------- Security headers ----------------
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    return response


app.include_router(auth_router.router)
app.include_router(standards_router.router)
app.include_router(recommend_router.router)
app.include_router(specs_router.router)
app.include_router(change_requests_router.router)
app.include_router(analytics_router.router)
app.include_router(users_router.router)
app.include_router(audit_router.router)


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        matching_engine.rebuild_index(db)
        logger.info(
            f"Index built: {len(matching_engine._indexed_standards)} standards. "
            f"Dense embeddings active: {matching_engine.is_semantic_embedding_active()}. "
            f"CORS allowed origins: {ALLOWED_ORIGINS}."
        )
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "index_ready": matching_engine.is_index_ready(),
        "standards_indexed": len(matching_engine._indexed_standards),
        "embeddings_active": matching_engine.is_semantic_embedding_active(),
    }
