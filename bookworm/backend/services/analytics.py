import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from collections import defaultdict

from sqlalchemy.orm import Session
import models


def calculate_wpm(words_read: int, duration_seconds: float) -> float:
    if duration_seconds <= 0:
        return 0.0
    return round((words_read / duration_seconds) * 60, 1)


def get_reading_stats(db: Session, user_id: int) -> Dict[str, Any]:
    # Book counts
    total_books = db.query(models.UserBook).filter_by(user_id=user_id).count()
    books_read = db.query(models.UserBook).filter_by(user_id=user_id, status=models.ShelfStatus.read).count()
    books_reading = db.query(models.UserBook).filter_by(user_id=user_id, status=models.ShelfStatus.reading).count()
    books_backlog = db.query(models.UserBook).filter_by(user_id=user_id, status=models.ShelfStatus.backlog).count()

    # Reading time
    sessions = db.query(models.ReadingSession).filter_by(user_id=user_id).all()
    total_seconds = sum(
        (s.ended_at - s.started_at).total_seconds()
        for s in sessions
        if s.started_at and s.ended_at
    )
    total_hours = round(total_seconds / 3600, 1)

    # Total words read
    total_words = sum(s.words_read or 0 for s in sessions)

    # Average WPM
    avg_wpm = calculate_wpm(total_words, total_seconds) if total_seconds > 0 else 0.0

    # Books this month
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    books_this_month = (
        db.query(models.UserBook)
        .filter(
            models.UserBook.user_id == user_id,
            models.UserBook.finished_at >= month_start,
        )
        .count()
    )

    return {
        "total_books": total_books,
        "books_read": books_read,
        "books_reading": books_reading,
        "books_backlog": books_backlog,
        "total_hours_read": total_hours,
        "total_words_read": total_words,
        "avg_wpm": avg_wpm,
        "books_this_month": books_this_month,
    }


def get_speed_over_time(db: Session, user_id: int) -> List[Dict[str, Any]]:
    sessions = (
        db.query(models.ReadingSession)
        .filter_by(user_id=user_id)
        .order_by(models.ReadingSession.started_at)
        .all()
    )

    # Group by week
    weekly: Dict[str, Dict] = defaultdict(lambda: {"words": 0, "seconds": 0})
    for s in sessions:
        if not s.started_at or not s.ended_at:
            continue
        week = s.started_at.strftime("%Y-W%W")
        duration = (s.ended_at - s.started_at).total_seconds()
        weekly[week]["words"] += s.words_read or 0
        weekly[week]["seconds"] += duration

    result = []
    for week, data in sorted(weekly.items()):
        wpm = calculate_wpm(data["words"], data["seconds"])
        result.append({"week": week, "wpm": wpm, "hours": round(data["seconds"] / 3600, 1)})
    return result


def get_genre_breakdown(db: Session, user_id: int) -> List[Dict[str, Any]]:
    user_books = db.query(models.UserBook).filter_by(user_id=user_id).all()
    genre_counts: Dict[str, int] = defaultdict(int)

    for ub in user_books:
        book = db.query(models.Book).filter_by(id=ub.book_id).first()
        if book and book.genres:
            try:
                genres = json.loads(book.genres)
                for g in genres:
                    if g:
                        genre_counts[g] += 1
            except Exception:
                pass

    total = sum(genre_counts.values()) or 1
    result = [
        {"genre": g, "count": c, "percentage": round(c / total * 100, 1)}
        for g, c in sorted(genre_counts.items(), key=lambda x: -x[1])
    ]
    return result


def get_recent_sessions(db: Session, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
    sessions = (
        db.query(models.ReadingSession)
        .filter_by(user_id=user_id)
        .order_by(models.ReadingSession.started_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for s in sessions:
        book = db.query(models.Book).filter_by(id=s.book_id).first()
        duration = 0.0
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds()
        result.append({
            "id": s.id,
            "book_id": s.book_id,
            "book_title": book.title if book else "Unknown",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "duration_minutes": round(duration / 60, 1),
            "words_read": s.words_read or 0,
            "pages_read": s.pages_read or 0,
            "wpm": calculate_wpm(s.words_read or 0, duration),
        })
    return result
