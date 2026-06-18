from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
import models

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


# ---------- Enums & Schemas ----------

class Period(str, Enum):
    week = "week"
    month = "month"
    season = "season"
    alltime = "alltime"


class Category(str, Enum):
    total_beers = "total_beers"
    unique_beers = "unique_beers"
    events_attended = "events_attended"
    longest_event = "longest_event"
    most_in_event = "most_in_event"
    streak = "streak"


class LeaderboardEntry(BaseModel):
    position: int
    user_id: int
    username: str
    display_name: str
    avatar_color: str
    value: float
    label: str = ""


class ShameEntry(BaseModel):
    position: int
    user_id: int
    username: str
    display_name: str
    avatar_color: str
    blackouts: int
    vomits: int
    total: int


# ---------- Helpers ----------

def _period_start(period: Period) -> Optional[datetime]:
    now = datetime.utcnow()
    if period == Period.week:
        return now - timedelta(days=now.weekday())
    elif period == Period.month:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == Period.season:
        month = now.month
        if month in (3, 4, 5):
            start_month = 3
        elif month in (6, 7, 8):
            start_month = 6
        elif month in (9, 10, 11):
            start_month = 9
        else:
            start_month = 12
            if month < 3:
                return datetime(now.year - 1, 12, 1)
        return datetime(now.year, start_month, 1)
    return None  # alltime


def _apply_period_filter(query, period: Period, date_col):
    start = _period_start(period)
    if start:
        query = query.filter(date_col >= start)
    return query


# ---------- Endpoints ----------

@router.get("", response_model=List[LeaderboardEntry])
def get_leaderboard(
    period: Period = Query(Period.week),
    category: Category = Query(Category.total_beers),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if category == Category.total_beers:
        return _total_beers(db, period)
    elif category == Category.unique_beers:
        return _unique_beers(db, period)
    elif category == Category.events_attended:
        return _events_attended(db, period)
    elif category == Category.longest_event:
        return _longest_event(db, period)
    elif category == Category.most_in_event:
        return _most_in_event(db, period)
    elif category == Category.streak:
        return _streak(db)
    return []


def _total_beers(db: Session, period: Period) -> List[LeaderboardEntry]:
    query = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.display_name,
            models.User.avatar_color,
            func.count(models.CheckIn.id).label("value"),
        )
        .join(models.CheckIn, models.CheckIn.user_id == models.User.id)
    )
    query = _apply_period_filter(query, period, models.CheckIn.created_at)
    rows = query.group_by(models.User.id).order_by(func.count(models.CheckIn.id).desc()).all()
    return [
        LeaderboardEntry(
            position=i + 1,
            user_id=r.id,
            username=r.username,
            display_name=r.display_name,
            avatar_color=r.avatar_color,
            value=r.value,
            label="beers",
        )
        for i, r in enumerate(rows)
    ]


def _unique_beers(db: Session, period: Period) -> List[LeaderboardEntry]:
    query = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.display_name,
            models.User.avatar_color,
            func.count(func.distinct(models.CheckIn.beer_name)).label("value"),
        )
        .join(models.CheckIn, models.CheckIn.user_id == models.User.id)
    )
    query = _apply_period_filter(query, period, models.CheckIn.created_at)
    rows = (
        query.group_by(models.User.id)
        .order_by(func.count(func.distinct(models.CheckIn.beer_name)).desc())
        .all()
    )
    return [
        LeaderboardEntry(
            position=i + 1,
            user_id=r.id,
            username=r.username,
            display_name=r.display_name,
            avatar_color=r.avatar_color,
            value=r.value,
            label="unique beers",
        )
        for i, r in enumerate(rows)
    ]


def _events_attended(db: Session, period: Period) -> List[LeaderboardEntry]:
    query = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.display_name,
            models.User.avatar_color,
            func.count(models.Event.id).label("value"),
        )
        .join(models.Event, models.Event.user_id == models.User.id)
    )
    query = _apply_period_filter(query, period, models.Event.started_at)
    rows = query.group_by(models.User.id).order_by(func.count(models.Event.id).desc()).all()
    return [
        LeaderboardEntry(
            position=i + 1,
            user_id=r.id,
            username=r.username,
            display_name=r.display_name,
            avatar_color=r.avatar_color,
            value=r.value,
            label="events",
        )
        for i, r in enumerate(rows)
    ]


def _longest_event(db: Session, period: Period) -> List[LeaderboardEntry]:
    # Duration in seconds for ended events
    subq = (
        db.query(
            models.Event.user_id,
            func.max(
                func.julianday(models.Event.ended_at) - func.julianday(models.Event.started_at)
            ).label("max_days"),
        )
        .filter(models.Event.ended_at.isnot(None))
    )
    subq = _apply_period_filter(subq, period, models.Event.started_at)
    subq = subq.group_by(models.Event.user_id).subquery()

    rows = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.display_name,
            models.User.avatar_color,
            subq.c.max_days,
        )
        .join(subq, subq.c.user_id == models.User.id)
        .order_by(subq.c.max_days.desc())
        .all()
    )
    return [
        LeaderboardEntry(
            position=i + 1,
            user_id=r.id,
            username=r.username,
            display_name=r.display_name,
            avatar_color=r.avatar_color,
            value=round((r.max_days or 0) * 24, 1),  # convert days to hours
            label="hours",
        )
        for i, r in enumerate(rows)
    ]


def _most_in_event(db: Session, period: Period) -> List[LeaderboardEntry]:
    # Max check-ins in a single event per user
    event_counts = (
        db.query(
            models.Event.user_id,
            models.Event.id.label("event_id"),
            func.count(models.CheckIn.id).label("cnt"),
        )
        .join(models.CheckIn, models.CheckIn.event_id == models.Event.id)
    )
    event_counts = _apply_period_filter(event_counts, period, models.Event.started_at)
    event_counts = event_counts.group_by(models.Event.id).subquery()

    max_per_user = (
        db.query(
            event_counts.c.user_id,
            func.max(event_counts.c.cnt).label("max_cnt"),
        )
        .group_by(event_counts.c.user_id)
        .subquery()
    )

    rows = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.display_name,
            models.User.avatar_color,
            max_per_user.c.max_cnt,
        )
        .join(max_per_user, max_per_user.c.user_id == models.User.id)
        .order_by(max_per_user.c.max_cnt.desc())
        .all()
    )
    return [
        LeaderboardEntry(
            position=i + 1,
            user_id=r.id,
            username=r.username,
            display_name=r.display_name,
            avatar_color=r.avatar_color,
            value=r.max_cnt or 0,
            label="beers in one event",
        )
        for i, r in enumerate(rows)
    ]


def _streak(db: Session) -> List[LeaderboardEntry]:
    """Consecutive weeks with at least one event, counting back from current week."""
    users = db.query(models.User).filter(models.User.is_active == True).all()
    entries = []
    now = datetime.utcnow()

    for user in users:
        events = (
            db.query(models.Event.started_at)
            .filter(models.Event.user_id == user.id)
            .order_by(models.Event.started_at.desc())
            .all()
        )
        if not events:
            continue

        # Build set of (year, iso_week) tuples
        weeks_with_events = set()
        for (started_at,) in events:
            iso = started_at.isocalendar()
            weeks_with_events.add((iso[0], iso[1]))

        # Count consecutive weeks backwards from current week
        streak_count = 0
        check_date = now
        while True:
            iso = check_date.isocalendar()
            if (iso[0], iso[1]) in weeks_with_events:
                streak_count += 1
                check_date -= timedelta(weeks=1)
            else:
                break

        if streak_count > 0:
            entries.append((user, streak_count))

    entries.sort(key=lambda x: x[1], reverse=True)
    return [
        LeaderboardEntry(
            position=i + 1,
            user_id=u.id,
            username=u.username,
            display_name=u.display_name,
            avatar_color=u.avatar_color,
            value=count,
            label="weeks",
        )
        for i, (u, count) in enumerate(entries)
    ]


@router.get("/shame", response_model=List[ShameEntry])
def get_shame_leaderboard(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(
            models.User.id,
            models.User.username,
            models.User.display_name,
            models.User.avatar_color,
            func.sum(case((models.Event.blacked_out == True, 1), else_=0)).label("blackouts"),
            func.sum(case((models.Event.vomited == True, 1), else_=0)).label("vomits"),
        )
        .join(models.Event, models.Event.user_id == models.User.id)
        .group_by(models.User.id)
        .having(
            (func.sum(case((models.Event.blacked_out == True, 1), else_=0)) > 0)
            | (func.sum(case((models.Event.vomited == True, 1), else_=0)) > 0)
        )
        .order_by(
            (
                func.sum(case((models.Event.blacked_out == True, 1), else_=0))
                + func.sum(case((models.Event.vomited == True, 1), else_=0))
            ).desc()
        )
        .all()
    )
    return [
        ShameEntry(
            position=i + 1,
            user_id=r.id,
            username=r.username,
            display_name=r.display_name,
            avatar_color=r.avatar_color,
            blackouts=r.blackouts,
            vomits=r.vomits,
            total=r.blackouts + r.vomits,
        )
        for i, r in enumerate(rows)
    ]
