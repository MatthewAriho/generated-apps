import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from database import get_db
from auth import get_current_user, decode_token
import models
from sqlalchemy.orm import Session

router = APIRouter()


@router.get("/reader/{book_id}/file")
def get_book_file(
    book_id: int,
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(lambda: None),
):
    # Accept token via query param (needed for epub.js which controls its own fetches)
    # or fall back to header-based auth
    user = None
    if token:
        payload = decode_token(token)
        if payload:
            username = payload.get("sub")
            if username:
                user = db.query(models.User).filter_by(username=username, is_active=True).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    book = db.query(models.Book).filter_by(id=book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    if not os.path.exists(book.file_path):
        raise HTTPException(status_code=404, detail="Book file not found on disk")

    media_type = "application/epub+zip" if book.file_type.value == "epub" else "application/pdf"
    filename = Path(book.file_path).name

    return FileResponse(
        path=book.file_path,
        media_type=media_type,
        filename=filename,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
