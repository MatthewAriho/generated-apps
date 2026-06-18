"""Background task to auto-end stale events.

Events with no check-in activity for 5+ hours are automatically ended.
Uses APScheduler to run every 30 minutes.
"""

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import SessionLocal
import models

INACTIVITY_THRESHOLD_HOURS = 5


def auto_end_stale_events():
    """Find active events with last check-in > 5h ago and end them."""
    db: Session = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=INACTIVITY_THRESHOLD_HOURS)

        # Subquery: last check-in time per active event
        last_checkin = (
            db.query(
                models.CheckIn.event_id,
                func.max(models.CheckIn.created_at).label("last_at"),
            )
            .group_by(models.CheckIn.event_id)
            .subquery()
        )

        # Active events where last check-in is older than cutoff
        stale_with_checkins = (
            db.query(models.Event)
            .join(last_checkin, last_checkin.c.event_id == models.Event.id)
            .filter(
                models.Event.is_active == True,
                last_checkin.c.last_at < cutoff,
            )
            .all()
        )

        # Active events with NO check-ins where started_at is older than cutoff
        events_with_checkins_ids = (
            db.query(models.CheckIn.event_id).distinct().subquery()
        )
        stale_without_checkins = (
            db.query(models.Event)
            .filter(
                models.Event.is_active == True,
                models.Event.started_at < cutoff,
                ~models.Event.id.in_(
                    db.query(events_with_checkins_ids.c.event_id)
                ),
            )
            .all()
        )

        all_stale = stale_with_checkins + stale_without_checkins
        for event in all_stale:
            event.is_active = False
            event.ended_at = datetime.utcnow()

        if all_stale:
            db.commit()
            print(f"[auto_end] Ended {len(all_stale)} stale event(s)")
    except Exception as e:
        db.rollback()
        print(f"[auto_end] Error: {e}")
    finally:
        db.close()
