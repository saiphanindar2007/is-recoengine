import datetime as dt
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/change-requests", tags=["change-requests"])


@router.get("", response_model=List[schemas.ChangeRequestOut])
def list_change_requests(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    q = db.query(models.StandardChangeRequest)
    if current_user.role.value == "OFFICER":
        q = q.filter(models.StandardChangeRequest.raised_by_id == current_user.id)
    if status_filter:
        q = q.filter(models.StandardChangeRequest.status == status_filter)
    return q.order_by(models.StandardChangeRequest.created_at.desc()).all()


@router.post("", response_model=schemas.ChangeRequestOut)
def create_change_request(
    request: Request,
    payload: schemas.ChangeRequestCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("OFFICER", "ADMIN", "AUDITOR")),
):
    cr = models.StandardChangeRequest(
        standard_is_number=payload.standard_is_number,
        raised_by_id=current_user.id,
        reason=payload.reason,
    )
    db.add(cr)
    db.commit()
    db.refresh(cr)
    auth.write_audit_log(db, current_user, "CHANGE_REQUEST_RAISED", "StandardChangeRequest", cr.id,
                          {"standard": payload.standard_is_number}, request.client.host if request.client else None)
    return cr


@router.put("/{cr_id}/resolve", response_model=schemas.ChangeRequestOut)
def resolve_change_request(
    request: Request,
    cr_id: int,
    payload: schemas.ChangeRequestResolve,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    cr = db.query(models.StandardChangeRequest).filter(models.StandardChangeRequest.id == cr_id).first()
    if not cr:
        raise HTTPException(status_code=404, detail="Change request not found.")
    cr.status = payload.status
    cr.resolution_note = payload.resolution_note
    cr.resolved_by_id = current_user.id
    cr.resolved_at = dt.datetime.now(dt.UTC)
    db.commit()
    db.refresh(cr)
    auth.write_audit_log(db, current_user, "CHANGE_REQUEST_RESOLVED", "StandardChangeRequest", cr.id,
                          {"status": payload.status}, request.client.host if request.client else None)
    return cr
