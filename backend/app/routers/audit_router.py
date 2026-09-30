from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("", response_model=List[schemas.AuditLogOut])
def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN", "AUDITOR")),
    action: Optional[str] = None,
    limit: int = Query(100, le=500),
):
    """Read-only, append-only trail of every administrative mutation on the
    platform — who did what, to what, and when. No endpoint anywhere in the
    API updates or deletes rows in this table."""
    q = db.query(models.AuditLog)
    if action:
        q = q.filter(models.AuditLog.action == action)
    return q.order_by(models.AuditLog.created_at.desc()).limit(limit).all()
