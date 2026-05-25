from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models
from services.analytics import get_reading_stats, get_speed_over_time, get_genre_breakdown, get_recent_sessions

router = APIRouter()


@router.get("/analytics/overview")
def overview(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_reading_stats(db, current_user.id)


@router.get("/analytics/speed")
def speed(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_speed_over_time(db, current_user.id)


@router.get("/analytics/genres")
def genres(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_genre_breakdown(db, current_user.id)


@router.get("/analytics/sessions")
def sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    return get_recent_sessions(db, current_user.id)
