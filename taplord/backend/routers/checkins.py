from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(tags=["checkins"])


# ---------- Schemas ----------

class CheckInCreate(BaseModel):
    beer_name: str = Field(..., min_length=1, max_length=200)
    size_ml: int = Field(..., gt=0)
    beer_style: Optional[str] = Field(None, max_length=100)
    brewery: Optional[str] = Field(None, max_length=200)
    rating: Optional[int] = Field(None, ge=1, le=5)
    notes: Optional[str] = None
    photo_url: Optional[str] = None


class CheckInResponse(BaseModel):
    id: int
    event_id: int
    user_id: int
    beer_id: Optional[int] = None
    beer_name: str
    beer_style: Optional[str] = None
    brewery: Optional[str] = None
    size_ml: int
    rating: Optional[int] = None
    notes: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Helpers ----------

def _get_user_event(event_id: int, user: models.User, db: Session) -> models.Event:
    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.user_id == user.id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


def _match_or_create_beer(
    beer_name: str,
    beer_style: Optional[str],
    brewery: Optional[str],
    user_id: int,
    db: Session,
) -> Optional[int]:
    """Try to match an existing beer by name+brewery, or create a new one."""
    query = db.query(models.Beer).filter(
        models.Beer.name.ilike(beer_name.strip())
    )
    if brewery:
        query = query.filter(models.Beer.brewery.ilike(brewery.strip()))
    existing = query.first()
    if existing:
        return existing.id

    beer = models.Beer(
        name=beer_name.strip(),
        brewery=brewery.strip() if brewery else None,
        style=beer_style.strip() if beer_style else None,
        created_by=user_id,
    )
    db.add(beer)
    db.flush()
    return beer.id


# ---------- Endpoints ----------

@router.post(
    "/events/{event_id}/checkins",
    response_model=CheckInResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_checkin(
    event_id: int,
    body: CheckInCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = _get_user_event(event_id, current_user, db)

    beer_id = _match_or_create_beer(
        body.beer_name, body.beer_style, body.brewery, current_user.id, db
    )

    checkin = models.CheckIn(
        event_id=event.id,
        user_id=current_user.id,
        beer_id=beer_id,
        beer_name=body.beer_name.strip(),
        beer_style=body.beer_style.strip() if body.beer_style else None,
        brewery=body.brewery.strip() if body.brewery else None,
        size_ml=body.size_ml,
        rating=body.rating,
        notes=body.notes,
        photo_url=body.photo_url,
    )
    db.add(checkin)
    db.commit()
    db.refresh(checkin)
    return CheckInResponse.model_validate(checkin)


@router.post(
    "/events/{event_id}/checkins/{checkin_id}/repeat",
    response_model=CheckInResponse,
    status_code=status.HTTP_201_CREATED,
)
def repeat_checkin(
    event_id: int,
    checkin_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = _get_user_event(event_id, current_user, db)

    original = db.query(models.CheckIn).filter(
        models.CheckIn.id == checkin_id,
        models.CheckIn.event_id == event.id,
        models.CheckIn.user_id == current_user.id,
    ).first()
    if not original:
        raise HTTPException(status_code=404, detail="Check-in not found")

    clone = models.CheckIn(
        event_id=event.id,
        user_id=current_user.id,
        beer_id=original.beer_id,
        beer_name=original.beer_name,
        beer_style=original.beer_style,
        brewery=original.brewery,
        size_ml=original.size_ml,
        rating=None,
        notes=None,
        photo_url=None,
    )
    db.add(clone)
    db.commit()
    db.refresh(clone)
    return CheckInResponse.model_validate(clone)


@router.get("/events/{event_id}/checkins", response_model=List[CheckInResponse])
def list_checkins(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_user_event(event_id, current_user, db)
    checkins = (
        db.query(models.CheckIn)
        .filter(models.CheckIn.event_id == event_id)
        .order_by(models.CheckIn.created_at.desc())
        .all()
    )
    return [CheckInResponse.model_validate(c) for c in checkins]


@router.delete("/checkins/{checkin_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_checkin(
    checkin_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    checkin = db.query(models.CheckIn).filter(
        models.CheckIn.id == checkin_id,
        models.CheckIn.user_id == current_user.id,
    ).first()
    if not checkin:
        raise HTTPException(status_code=404, detail="Check-in not found")
    db.delete(checkin)
    db.commit()
