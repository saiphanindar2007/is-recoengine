import enum
import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Enum, JSON, Float, Boolean
)
from sqlalchemy.orm import relationship

from .database import Base


class RoleEnum(str, enum.Enum):
    ADMIN = "ADMIN"                 # BIS / DoCA Standards Custodian
    OFFICER = "OFFICER"             # Procurement Officer
    AUDITOR = "AUDITOR"             # Compliance Auditor / Analytics viewer


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(120), nullable=False)
    email = Column(String(180), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.OFFICER)
    department = Column(String(180), nullable=True)
    designation = Column(String(120), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    saved_specs = relationship("SavedSpecification", back_populates="owner", cascade="all,delete")
    queries = relationship("QueryLog", back_populates="user", cascade="all,delete")


class Standard(Base):
    __tablename__ = "standards"

    id = Column(Integer, primary_key=True, index=True)
    is_number = Column(String(80), unique=True, index=True, nullable=False)
    title = Column(String(400), nullable=False)
    category = Column(String(120), index=True, nullable=False)
    scope = Column(Text, nullable=False)
    latest_version = Column(String(200))
    amendments = Column(JSON, default=list)
    allied_standards = Column(JSON, default=list)       # list of is_number strings
    normative_references = Column(JSON, default=list)
    certification = Column(JSON, default=list)
    keywords = Column(JSON, default=list)
    status = Column(String(30), default="PUBLISHED")     # PUBLISHED | DRAFT | UNDER_REVIEW | WITHDRAWN
    is_current = Column(Boolean, default=True)            # False = known superseded/outdated
    superseded_by = Column(String(80), nullable=True)     # IS number of the replacing standard, if any
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    # --- Data provenance / evidence trail ---
    # source_reference: where this record's data was sourced from (e.g. a BIS
    # catalogue page URL, gazette notification number, or "BIS Standards
    # Catalogue, manually verified"). Free text, not a hard link requirement,
    # since a real BIS bulk feed is the eventual source but isn't available yet.
    source_reference = Column(String(500), nullable=True)
    # last_verified_at / verified_by_id: when a human custodian last confirmed
    # this record (title/scope/version/amendments/certification) is accurate
    # against the source above. NULL means "never verified" and is surfaced
    # to the officer as an explicit warning rather than silently treated as
    # trustworthy — the recommendation engine is advisory, and unverified
    # catalogue data is a real source of risk that shouldn't be hidden.
    last_verified_at = Column(DateTime, nullable=True)
    verified_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class QueryLog(Base):
    """Every recommendation request, for analytics + the learning-loop roadmap."""
    __tablename__ = "query_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    query_text = Column(Text, nullable=False)
    normalized_query = Column(Text, nullable=True)
    detected_script = Column(String(30), nullable=True)
    embeddings_used = Column(Boolean, default=False)
    top_match_is_number = Column(String(80), nullable=True)
    top_match_score = Column(Float, nullable=True)
    result_count = Column(Integer, default=0)
    category_filter = Column(String(120), nullable=True)
    source = Column(String(30), default="TEXT")  # TEXT | DOCUMENT_UPLOAD
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    user = relationship("User", back_populates="queries")


class AuditLog(Base):
    """Append-only record of every mutating administrative action, independent
    of QueryLog (which only tracks search usage). Nothing updates or deletes
    rows in this table through the API — it is write-once by design."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_email = Column(String(180), nullable=True)
    actor_role = Column(String(30), nullable=True)
    action = Column(String(60), nullable=False)     # e.g. STANDARD_CREATE, USER_DEACTIVATE
    target_type = Column(String(60), nullable=False)  # e.g. Standard, User, ChangeRequest
    target_id = Column(String(120), nullable=True)
    detail = Column(JSON, default=dict)              # before/after snapshot or free-form context
    ip_address = Column(String(60), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)


class RevokedToken(Base):
    """JWT ids (jti) that have been explicitly logged out / revoked before
    their natural expiry, checked on every authenticated request."""
    __tablename__ = "revoked_tokens"

    id = Column(Integer, primary_key=True, index=True)
    jti = Column(String(64), unique=True, index=True, nullable=False)
    revoked_at = Column(DateTime, default=dt.datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class SavedSpecification(Base):
    """An officer's curated tender specification package built from recommendations."""
    __tablename__ = "saved_specifications"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    source_query = Column(Text, nullable=True)
    standard_numbers = Column(JSON, default=list)   # list of is_number strings chosen for the tender
    notes = Column(Text, nullable=True)
    status = Column(String(30), default="DRAFT")     # DRAFT | FINALIZED
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    updated_at = Column(DateTime, default=dt.datetime.utcnow, onupdate=dt.datetime.utcnow)

    owner = relationship("User", back_populates="saved_specs")


class StandardChangeRequest(Base):
    """Officers can flag a standard as outdated/incorrect; Admins review and resolve it —
    a real cross-role workflow rather than a static catalogue."""
    __tablename__ = "change_requests"

    id = Column(Integer, primary_key=True, index=True)
    standard_is_number = Column(String(80), nullable=False)
    raised_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String(30), default="OPEN")   # OPEN | IN_REVIEW | RESOLVED | REJECTED
    resolution_note = Column(Text, nullable=True)
    resolved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=dt.datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
