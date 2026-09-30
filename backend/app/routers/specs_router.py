from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/specifications", tags=["specifications"])


@router.get("", response_model=List[schemas.SavedSpecOut])
def list_specs(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    q = db.query(models.SavedSpecification)
    if current_user.role.value != "ADMIN":
        q = q.filter(models.SavedSpecification.owner_id == current_user.id)
    return q.order_by(models.SavedSpecification.updated_at.desc()).all()


@router.post("", response_model=schemas.SavedSpecOut)
def create_spec(
    payload: schemas.SavedSpecCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_roles("OFFICER", "ADMIN")),
):
    spec = models.SavedSpecification(owner_id=current_user.id, **payload.model_dump())
    db.add(spec)
    db.commit()
    db.refresh(spec)
    return spec


@router.put("/{spec_id}", response_model=schemas.SavedSpecOut)
def update_spec(
    spec_id: int,
    payload: schemas.SavedSpecUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    spec = db.query(models.SavedSpecification).filter(models.SavedSpecification.id == spec_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found.")
    if spec.owner_id != current_user.id and current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="You can only edit your own specifications.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(spec, field, value)
    db.commit()
    db.refresh(spec)
    return spec


@router.delete("/{spec_id}")
def delete_spec(
    spec_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    spec = db.query(models.SavedSpecification).filter(models.SavedSpecification.id == spec_id).first()
    if not spec:
        raise HTTPException(status_code=404, detail="Specification not found.")
    if spec.owner_id != current_user.id and current_user.role.value != "ADMIN":
        raise HTTPException(status_code=403, detail="You can only delete your own specifications.")
    db.delete(spec)
    db.commit()
    return {"deleted": spec_id}
