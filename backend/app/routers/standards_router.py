from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from .. import models, schemas, auth, matching_engine
from ..database import get_db

router = APIRouter(prefix="/api/standards", tags=["standards"])


@router.get("", response_model=List[schemas.StandardOut])
def list_standards(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
    category: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    only_current: bool = False,
):
    q = db.query(models.Standard)
    if category:
        q = q.filter(models.Standard.category == category)

    # SECURITY: the PUBLISHED-only restriction for non-admins must be
    # unconditional. The previous version only applied it in an `elif`
    # branch that was skipped whenever a `status` query param was present —
    # so a non-admin could pass `?status=DRAFT` (or UNDER_REVIEW/WITHDRAWN)
    # and see records they should never have visibility into, the exact
    # kind of catalogue-visibility bypass already fixed for direct-by-number
    # fetch. Non-admins are now always constrained to PUBLISHED regardless
    # of what `status` they ask for; only ADMIN's `status` filter is honoured.
    if current_user.role.value != "ADMIN":
        q = q.filter(models.Standard.status == "PUBLISHED")
    elif status_filter:
        q = q.filter(models.Standard.status == status_filter)

    if only_current:
        q = q.filter(models.Standard.is_current.is_(True))
    if search:
        like = f"%{search}%"
        q = q.filter(
            (models.Standard.title.ilike(like)) | (models.Standard.is_number.ilike(like))
        )
    return q.order_by(models.Standard.is_number).all()


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    rows = db.query(models.Standard.category).filter(models.Standard.status == "PUBLISHED").distinct().all()
    return {"categories": sorted({r[0] for r in rows if r[0]})}


@router.get("/{is_number:path}", response_model=schemas.StandardOut)
def get_standard(is_number: str, db: Session = Depends(get_db),
                  current_user: models.User = Depends(auth.get_current_user)):
    """Fetch a single standard by its IS number.

    SECURITY: this must enforce the SAME visibility rule as list_standards()
    — non-ADMIN callers may only ever see PUBLISHED standards. A previous
    version of this endpoint had no status check at all, which meant any
    authenticated OFFICER/AUDITOR could read a DRAFT, UNDER_REVIEW, or
    WITHDRAWN standard (including one never publicly listed) simply by
    guessing/knowing its IS number — a direct-object-reference authorization
    bypass of the access control that list_standards() otherwise enforces.
    Treating an unauthorized-but-existing standard as 404 (rather than 403)
    also avoids confirming to a non-admin caller that a non-public standard
    exists at all.
    """
    std = db.query(models.Standard).filter(models.Standard.is_number == is_number).first()
    if not std or (std.status != "PUBLISHED" and current_user.role.value != "ADMIN"):
        raise HTTPException(status_code=404, detail="Standard not found.")
    return std


@router.post("", response_model=schemas.StandardOut)
def create_standard(
    request: Request,
    payload: schemas.StandardCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    existing = db.query(models.Standard).filter(models.Standard.is_number == payload.is_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="A standard with this IS number already exists.")
    std = models.Standard(**payload.model_dump(), created_by_id=current_user.id)
    db.add(std)
    db.commit()
    db.refresh(std)
    matching_engine.rebuild_index(db)
    auth.write_audit_log(db, current_user, "STANDARD_CREATE", "Standard", std.is_number,
                          {"title": std.title, "category": std.category},
                          request.client.host if request.client else None)
    return std


@router.put("/{is_number:path}/verify", response_model=schemas.StandardOut)
def verify_standard(
    request: Request,
    is_number: str,
    payload: schemas.StandardVerify,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    """Explicit human-verification action: an ADMIN (Standards Custodian)
    confirms this record's data has been checked against its source and
    stamps `last_verified_at` / `verified_by_id` accordingly. This is
    deliberately a separate endpoint from PUT (general edit) rather than an
    implicit side-effect of every edit, so "verified" means someone actually
    reviewed the record just now, not merely that a field was touched.

    ROUTING NOTE: this route MUST be registered before the generic
    PUT /{is_number:path} route below. `:path` converters match greedily
    (including any further "/" segments), so if the generic PUT route were
    registered first, `PUT /api/standards/IS 1234:2024/verify` would be
    swallowed by it with `is_number="IS 1234:2024/verify"` instead of ever
    reaching this endpoint — the same class of routing bug previously fixed
    for GET (IS numbers containing slashes), now avoided here by ordering.
    """
    std = db.query(models.Standard).filter(models.Standard.is_number == is_number).first()
    if not std:
        raise HTTPException(status_code=404, detail="Standard not found.")

    import datetime as _dt
    std.last_verified_at = _dt.datetime.now(_dt.UTC)
    std.verified_by_id = current_user.id
    if payload.source_reference:
        std.source_reference = payload.source_reference
    db.commit()
    db.refresh(std)
    auth.write_audit_log(db, current_user, "STANDARD_VERIFIED", "Standard", is_number,
                          {"source_reference": std.source_reference, "note": payload.note},
                          request.client.host if request.client else None)
    return std


@router.put("/{is_number:path}", response_model=schemas.StandardOut)
def update_standard(
    request: Request,
    is_number: str,
    payload: schemas.StandardUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    std = db.query(models.Standard).filter(models.Standard.is_number == is_number).first()
    if not std:
        raise HTTPException(status_code=404, detail="Standard not found.")

    changes = payload.model_dump(exclude_unset=True)
    before = {k: getattr(std, k) for k in changes.keys()}
    for field, value in changes.items():
        setattr(std, field, value)

    # Editing substantive content invalidates a prior human verification —
    # `last_verified_at` should mean "verified as it stands today," not "was
    # verified at some point before someone changed the data underneath it."
    _CONTENT_FIELDS = {
        "title", "scope", "latest_version", "amendments", "allied_standards",
        "normative_references", "certification", "is_current", "superseded_by",
    }
    if _CONTENT_FIELDS.intersection(changes.keys()) and std.last_verified_at is not None:
        std.last_verified_at = None
        std.verified_by_id = None

    db.commit()
    db.refresh(std)
    matching_engine.rebuild_index(db)
    auth.write_audit_log(db, current_user, "STANDARD_UPDATE", "Standard", is_number,
                          {"before": before, "after": changes},
                          request.client.host if request.client else None)
    return std


@router.delete("/{is_number:path}")
def delete_standard(
    request: Request,
    is_number: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    std = db.query(models.Standard).filter(models.Standard.is_number == is_number).first()
    if not std:
        raise HTTPException(status_code=404, detail="Standard not found.")
    db.delete(std)
    db.commit()
    matching_engine.rebuild_index(db)
    auth.write_audit_log(db, current_user, "STANDARD_DELETE", "Standard", is_number, {},
                          request.client.host if request.client else None)
    return {"deleted": is_number}
