from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db
from ..rate_limit import limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenOut)
@limiter.limit("10/hour")
def register(request: Request, payload: schemas.UserCreate, db: Session = Depends(get_db)):
    """Public self-registration is intentionally locked to the OFFICER role.
    Privilege escalation via the public endpoint (e.g. registering as ADMIN)
    is rejected outright rather than silently downgraded, so the caller gets
    an explicit, honest error instead of a surprising role. ADMIN and AUDITOR
    accounts can only be created by an existing ADMIN via POST /api/users."""
    requested_role = payload.role.upper()
    if requested_role != "OFFICER":
        raise HTTPException(
            status_code=400,
            detail="Public registration is limited to Procurement Officer accounts. "
                   "Standards Custodian or Compliance Auditor accounts must be created "
                   "by an existing Standards Custodian.",
        )

    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    user = models.User(
        full_name=payload.full_name,
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        role="OFFICER",
        department=payload.department,
        designation=payload.designation,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    auth.write_audit_log(db, user, "USER_REGISTER", "User", user.id,
                          {"role": "OFFICER"}, request.client.host if request.client else None)

    token = auth.create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.TokenOut(access_token=token, expires_in_minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES,
                             user=schemas.UserOut.model_validate(user))


@router.post("/login", response_model=schemas.TokenOut)
@limiter.limit("20/minute")
def login(request: Request, payload: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not auth.verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account has been deactivated.")

    token = auth.create_access_token({"sub": str(user.id), "role": user.role.value})
    return schemas.TokenOut(access_token=token, expires_in_minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES,
                             user=schemas.UserOut.model_validate(user))


@router.post("/logout")
def logout(
    token: str = Depends(auth.get_current_token_raw),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    auth.revoke_token(db, token)
    return {"detail": "Signed out. This session token has been revoked."}


@router.get("/me", response_model=schemas.UserOut)
def me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user
