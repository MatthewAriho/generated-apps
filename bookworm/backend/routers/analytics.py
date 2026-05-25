from datetime import datetime, timedelta
from typing import List

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


@router.get("/analytics/streak")
def streak(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Returns current streak (consecutive days with a reading session)
    and a 30-day activity heatmap."""
    sessions = (
        db.query(models.ReadingSession)
        .filter_by(user_id=current_user.id)
        .order_by(models.ReadingSession.started_at.desc())
        .all()
    )

    # Build set of dates with reading activity
    active_dates = set()
    for s in sessions:
        if s.started_at:
            active_dates.add(s.started_at.date())

    # Calculate current streak
    today = datetime.utcnow().date()
    current_streak = 0
    check_date = today
    while check_date in active_dates:
        current_streak += 1
        check_date -= timedelta(days=1)
    # If today has no session but yesterday does, check from yesterday
    if current_streak == 0:
        check_date = today - timedelta(days=1)
        while check_date in active_dates:
            current_streak += 1
            check_date -= timedelta(days=1)

    # Longest streak
    if active_dates:
        sorted_dates = sorted(active_dates)
        longest = 1
        run = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i-1]).days == 1:
                run += 1
                longest = max(longest, run)
            else:
                run = 1
    else:
        longest = 0

    # Last 30 days heatmap
    heatmap: List[dict] = []
    for i in range(29, -1, -1):
        d = today - timedelta(days=i)
        heatmap.append({"date": d.isoformat(), "active": d in active_dates})

    return {
        "current_streak": current_streak,
        "longest_streak": longest,
        "today_active": today in active_dates,
        "heatmap": heatmap,
    }
