from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models
from models import EventType

router = APIRouter(prefix="/events", tags=["events"])


# ---------- Schemas ----------

class EventCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    event_type: EventType = EventType.night_out


class EventUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    event_type: Optional[EventType] = None
    venue_description: Optional[str] = None
    blacked_out: Optional[bool] = None
    vomited: Optional[bool] = None
    ended_at: Optional[datetime] = None


class CheckInBrief(BaseModel):
    id: int
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


class EventResponse(BaseModel):
    id: int
    user_id: int
    name: str
    event_type: EventType
    started_at: datetime
    ended_at: Optional[datetime] = None
    is_active: bool
    blacked_out: bool
    vomited: bool
    venue_description: Optional[str] = None
    checkin_count: int = 0

    class Config:
        from_attributes = True


class EventDetail(EventResponse):
    checkins: List[CheckInBrief] = []


# ---------- Helpers ----------

def _get_user_event(event_id: int, user: models.User, db: Session) -> models.Event:
    event = db.query(models.Event).filter(
        models.Event.id == event_id,
        models.Event.user_id == user.id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


# ---------- Endpoints ----------

@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
def create_event(
    body: EventCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = models.Event(
        user_id=current_user.id,
        name=body.name.strip(),
        event_type=body.event_type,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return EventResponse(
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        checkin_count=0,
    )


@router.get("", response_model=List[EventResponse])
def list_events(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.Event, func.count(models.CheckIn.id).label("checkin_count"))
        .outerjoin(models.CheckIn, models.CheckIn.event_id == models.Event.id)
        .filter(models.Event.user_id == current_user.id)
        .group_by(models.Event.id)
        .order_by(models.Event.started_at.desc())
        .all()
    )
    results = []
    for event, count in rows:
        results.append(EventResponse(
            **{c.name: getattr(event, c.name) for c in event.__table__.columns},
            checkin_count=count,
        ))
    return results


@router.get("/active", response_model=Optional[EventDetail])
def get_active_event(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = db.query(models.Event).filter(
        models.Event.user_id == current_user.id,
        models.Event.is_active == True,
    ).order_by(models.Event.started_at.desc()).first()
    if not event:
        return None
    checkins = (
        db.query(models.CheckIn)
        .filter(models.CheckIn.event_id == event.id)
        .order_by(models.CheckIn.created_at.desc())
        .all()
    )
    return EventDetail(
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        checkin_count=len(checkins),
        checkins=[CheckInBrief.model_validate(c) for c in checkins],
    )


@router.get("/{event_id}", response_model=EventDetail)
def get_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = _get_user_event(event_id, current_user, db)
    checkins = (
        db.query(models.CheckIn)
        .filter(models.CheckIn.event_id == event.id)
        .order_by(models.CheckIn.created_at.desc())
        .all()
    )
    return EventDetail(
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        checkin_count=len(checkins),
        checkins=[CheckInBrief.model_validate(c) for c in checkins],
    )


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: int,
    body: EventUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = _get_user_event(event_id, current_user, db)
    update_data = body.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)
    db.commit()
    db.refresh(event)
    count = db.query(func.count(models.CheckIn.id)).filter(
        models.CheckIn.event_id == event.id
    ).scalar()
    return EventResponse(
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        checkin_count=count,
    )


@router.post("/{event_id}/end", response_model=EventResponse)
def end_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = _get_user_event(event_id, current_user, db)
    if not event.is_active:
        raise HTTPException(status_code=400, detail="Event already ended")
    event.is_active = False
    event.ended_at = datetime.utcnow()
    db.commit()
    db.refresh(event)
    count = db.query(func.count(models.CheckIn.id)).filter(
        models.CheckIn.event_id == event.id
    ).scalar()
    return EventResponse(
        **{c.name: getattr(event, c.name) for c in event.__table__.columns},
        checkin_count=count,
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    event = _get_user_event(event_id, current_user, db)
    db.delete(event)
    db.commit()
