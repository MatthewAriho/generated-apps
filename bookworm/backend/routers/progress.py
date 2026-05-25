from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models

router = APIRouter()


class ProgressUpdate(BaseModel):
    position: str
    percentage: float
    words_read: Optional[int] = 0
    pages_read: Optional[int] = 0
    session_start: Optional[datetime] = None
    session_end: Optional[datetime] = None


class ProgressResponse(BaseModel):
    book_id: int
    position: Optional[str]
    percentage: float
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("/progress/{book_id}", response_model=ProgressResponse)
def get_progress(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    book = db.query(models.Book).filter_by(id=book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    progress = db.query(models.ReadingProgress).filter_by(
        user_id=current_user.id, book_id=book_id
    ).first()

    if not progress:
        return {"book_id": book_id, "position": None, "percentage": 0.0, "updated_at": datetime.utcnow()}
    return {"book_id": book_id, "position": progress.position, "percentage": progress.percentage, "updated_at": progress.updated_at}


@router.post("/progress/{book_id}", response_model=ProgressResponse)
def update_progress(
    book_id: int,
    body: ProgressUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    book = db.query(models.Book).filter_by(id=book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    progress = db.query(models.ReadingProgress).filter_by(
        user_id=current_user.id, book_id=book_id
    ).first()

    if not progress:
        progress = models.ReadingProgress(user_id=current_user.id, book_id=book_id)
        db.add(progress)

    progress.position = body.position
    progress.percentage = body.percentage
    progress.updated_at = datetime.utcnow()

    # Log session if times provided
    if body.session_start and body.session_end:
        session = models.ReadingSession(
            user_id=current_user.id,
            book_id=book_id,
            started_at=body.session_start,
            ended_at=body.session_end,
            words_read=body.words_read or 0,
            pages_read=body.pages_read or 0,
        )
        db.add(session)

    # Update shelf status to reading if not already read
    ub = db.query(models.UserBook).filter_by(user_id=current_user.id, book_id=book_id).first()
    if ub and ub.status == models.ShelfStatus.backlog:
        ub.status = models.ShelfStatus.reading
        ub.started_at = ub.started_at or datetime.utcnow()

    db.commit()
    db.refresh(progress)
    return {"book_id": book_id, "position": progress.position, "percentage": progress.percentage, "updated_at": progress.updated_at}
