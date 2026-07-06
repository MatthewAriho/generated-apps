import json
from datetime import datetime, timedelta
from typing import List
from collections import defaultdict

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


@router.get("/analytics/profile")
def reading_profile(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Build a user reading profile: top genres, reading pace, and recommendations."""
    user_books = db.query(models.UserBook).filter_by(user_id=current_user.id).all()
    sessions = db.query(models.ReadingSession).filter_by(user_id=current_user.id).all()

    # Top genres
    genre_counts: dict = defaultdict(int)
    for ub in user_books:
        book = db.query(models.Book).filter_by(id=ub.book_id).first()
        if book and book.genres:
            try:
                for g in json.loads(book.genres):
                    if g:
                        genre_counts[g] += 1
            except Exception:
                pass

    top_genres = sorted(genre_counts.items(), key=lambda x: -x[1])[:5]

    # Reading pace
    total_seconds = sum(
        (s.ended_at - s.started_at).total_seconds()
        for s in sessions if s.started_at and s.ended_at
    )
    total_books_finished = sum(1 for ub in user_books if ub.status == models.ShelfStatus.read)
    avg_days_per_book = 0
    if total_books_finished > 0:
        finished_books = [ub for ub in user_books if ub.status == models.ShelfStatus.read and ub.started_at and ub.finished_at]
        if finished_books:
            total_reading_days = sum((ub.finished_at - ub.started_at).days for ub in finished_books)
            avg_days_per_book = round(total_reading_days / len(finished_books), 1)

    # Recommendations: unread books from user's library matching top genres
    read_book_ids = {ub.book_id for ub in user_books if ub.status == models.ShelfStatus.read}
    reading_book_ids = {ub.book_id for ub in user_books if ub.status == models.ShelfStatus.reading}
    backlog_ids = {ub.book_id for ub in user_books if ub.status == models.ShelfStatus.backlog}

    recommendations = []
    if top_genres and backlog_ids:
        top_genre_names = {g for g, _ in top_genres[:3]}
        for book_id in backlog_ids:
            book = db.query(models.Book).filter_by(id=book_id).first()
            if not book or not book.genres:
                continue
            try:
                book_genres = set(json.loads(book.genres))
            except Exception:
                continue
            overlap = book_genres & top_genre_names
            if overlap:
                recommendations.append({
                    "book_id": book.id,
                    "title": book.title,
                    "author": book.author,
                    "cover_url": f"/bookworm{book.cover_url}" if book.cover_url else None,
                    "reason": f"Matches your interest in {', '.join(overlap)}",
                })
            if len(recommendations) >= 5:
                break

    # Search suggestions based on top genres
    search_suggestions = [g for g, _ in top_genres[:5]]

    return {
        "top_genres": [{"genre": g, "count": c} for g, c in top_genres],
        "books_finished": total_books_finished,
        "avg_days_per_book": avg_days_per_book,
        "total_hours_read": round(total_seconds / 3600, 1),
        "recommendations": recommendations,
        "search_suggestions": search_suggestions,
    }
