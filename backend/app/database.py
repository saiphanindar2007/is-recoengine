import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./is_reco.db")

connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=connect_args)
# expire_on_commit=False: the matching engine caches ORM Standard objects
# in-memory across requests (as the live semantic index). With the default
# expire_on_commit=True, those cached objects get marked stale after any
# commit and raise DetachedInstanceError the next time an attribute is
# accessed from a different request's session. Since the index is rebuilt
# from a fresh query on every mutation anyway, this is safe.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
