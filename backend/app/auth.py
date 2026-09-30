import os
import uuid
import datetime as dt
import logging
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from . import models
from .database import get_db

logger = logging.getLogger("is_reco.auth")

APP_ENV = os.environ.get("APP_ENV", "development")
_DEFAULT_DEV_SECRET = "is-recoengine-dev-secret-change-in-production"
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", _DEFAULT_DEV_SECRET)

if APP_ENV == "production" and SECRET_KEY == _DEFAULT_DEV_SECRET:
    # Fail loudly rather than silently run production on a known/default secret.
    raise RuntimeError(
        "JWT_SECRET_KEY must be set to a strong, unique value when APP_ENV=production. "
        "Refusing to start with the default development secret."
    )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "480"))  # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    jti = uuid.uuid4().hex
    to_encode.update({"exp": expire, "jti": jti})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def revoke_token(db: Session, token: str):
    payload = decode_token(token)
    if not payload:
        return
    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        return
    existing = db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first()
    if existing:
        return
    db.add(models.RevokedToken(jti=jti, expires_at=dt.datetime.fromtimestamp(exp, dt.UTC)))
    db.commit()


def _is_revoked(db: Session, jti: str) -> bool:
    if not jti:
        return False
    return db.query(models.RevokedToken).filter(models.RevokedToken.jti == jti).first() is not None


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception
    if _is_revoked(db, payload.get("jti")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This session has been signed out. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


def get_current_token_raw(token: str = Depends(oauth2_scheme)) -> str:
    return token


def require_roles(*roles: str):
    def dependency(user: models.User = Depends(get_current_user)) -> models.User:
        if user.role.value not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of the roles: {', '.join(roles)}",
            )
        return user
    return dependency


def write_audit_log(
    db: Session, actor: Optional[models.User], action: str, target_type: str,
    target_id: Optional[str] = None, detail: Optional[dict] = None, ip_address: Optional[str] = None,
):
    """Append-only audit trail. Never call db.query(AuditLog)...delete() /
    update() anywhere in the codebase — this table is write-once by design."""
    entry = models.AuditLog(
        actor_id=actor.id if actor else None,
        actor_email=actor.email if actor else None,
        actor_role=actor.role.value if actor else None,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        detail=detail or {},
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
