from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=schemas.UserOut)
def create_staff_account(
    request: Request,
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    """The ONLY way to create an ADMIN or AUDITOR account. Public /api/auth/register
    is locked to OFFICER — elevated roles require an existing Standards Custodian
    to explicitly grant them, closing the privilege-escalation gap where anyone
    could previously self-register as ADMIN."""
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    role = payload.role.upper()
    if role not in [r.value for r in models.RoleEnum]:
        raise HTTPException(status_code=400, detail="Invalid role selected.")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        role=role,
        department=payload.department,
        designation=payload.designation,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    auth.write_audit_log(db, current_user, "STAFF_ACCOUNT_CREATED", "User", user.id,
                          {"email": user.email, "role": role}, request.client.host if request.client else None)
    return user


@router.get("", response_model=List[schemas.UserOut])
def list_users(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_roles("ADMIN"))):
    return db.query(models.User).order_by(models.User.created_at.desc()).all()


@router.put("/{user_id}/deactivate", response_model=schemas.UserOut)
def deactivate_user(
    request: Request, user_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active = False
    db.commit()
    db.refresh(user)
    auth.write_audit_log(db, current_user, "USER_DEACTIVATE", "User", user.id, {"email": user.email},
                          request.client.host if request.client else None)
    return user


@router.put("/{user_id}/activate", response_model=schemas.UserOut)
def activate_user(
    request: Request, user_id: int, db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("ADMIN")),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = True
    db.commit()
    db.refresh(user)
    auth.write_audit_log(db, current_user, "USER_ACTIVATE", "User", user.id, {"email": user.email},
                          request.client.host if request.client else None)
    return user
