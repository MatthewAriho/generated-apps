import os
import json
import shutil
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from auth import get_current_user
import models
from services.metadata import extract_epub_metadata, extract_pdf_metadata, fetch_openlibrary_cover

router = APIRouter()

DATA_PATH = os.getenv("DATA_PATH", "/data")


class ShelfRequest(BaseModel):
    status: str
    rating: Optional[int] = None


class BookUpdateRequest(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    genres: Optional[List[str]] = None


class BookResponse(BaseModel):
    id: int
    title: str
    author: Optional[str]
    isbn: Optional[str]
    cover_url: Optional[str]
    file_type: str
    total_pages: Optional[int]
    total_words: Optional[int]
    genres: Optional[List[str]]
    added_at: datetime
    shelf_status: Optional[str] = None
    progress_percentage: Optional[float] = None

    class Config:
        from_attributes = True


def book_to_response(book: models.Book, user_book: Optional[models.UserBook], progress: Optional[models.ReadingProgress]) -> dict:
    genres = []
    if book.genres:
        try:
            genres = json.loads(book.genres)
        except Exception:
            genres = []
    return {
        "id": book.id,
        "title": book.title,
        "author": book.author,
        "isbn": book.isbn,
        "cover_url": f"/bookworm{book.cover_url}" if book.cover_url else None,
        "file_type": book.file_type.value if hasattr(book.file_type, "value") else book.file_type,
        "total_pages": book.total_pages,
        "total_words": book.total_words,
        "genres": genres,
        "added_at": book.added_at,
        "shelf_status": user_book.status.value if user_book and hasattr(user_book.status, "value") else (user_book.status if user_book else None),
        "progress_percentage": progress.percentage if progress else None,
    }


@router.post("/books/upload", response_model=BookResponse, status_code=201)
async def upload_book(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower().lstrip(".")
    if ext not in ("epub", "pdf"):
        raise HTTPException(status_code=400, detail="Only epub and pdf files are supported")

    # Save file
    books_dir = Path(f"{DATA_PATH}/books")
    books_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{datetime.utcnow().timestamp()}_{file.filename.replace(' ', '_')}"
    file_path = books_dir / safe_name

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract metadata
    meta = {}
    try:
        if ext == "epub":
            meta = extract_epub_metadata(str(file_path))
        else:
            meta = extract_pdf_metadata(str(file_path))
    except Exception as e:
        meta = {"title": Path(file.filename).stem, "author": None, "isbn": None}

    # Fetch/save cover
    cover_url = None
    cover_bytes = meta.get("cover_bytes")
    if not cover_bytes and meta.get("isbn"):
        cover_bytes = fetch_openlibrary_cover(meta["isbn"])
    if not cover_bytes and meta.get("title"):
        cover_bytes = fetch_openlibrary_cover(meta["title"])

    if cover_bytes:
        covers_dir = Path(f"{DATA_PATH}/covers")
        covers_dir.mkdir(parents=True, exist_ok=True)
        cover_filename = f"{safe_name}.jpg"
        cover_path = covers_dir / cover_filename
        with open(cover_path, "wb") as f:
            f.write(cover_bytes)
        cover_url = f"/covers/{cover_filename}"

    book = models.Book(
        title=meta.get("title") or Path(file.filename).stem,
        author=meta.get("author"),
        isbn=meta.get("isbn"),
        cover_url=cover_url,
        file_path=str(file_path),
        file_type=models.FileType(ext),
        total_pages=meta.get("total_pages"),
        total_words=meta.get("total_words"),
        genres=json.dumps(meta.get("genres", [])),
        added_by=current_user.id,
    )
    db.add(book)
    db.commit()
    db.refresh(book)

    # Add to user's shelf as backlog
    user_book = models.UserBook(
        user_id=current_user.id,
        book_id=book.id,
        status=models.ShelfStatus.backlog,
    )
    db.add(user_book)
    db.commit()
    db.refresh(user_book)

    return book_to_response(book, user_book, None)


@router.get("/books", response_model=List[BookResponse])
def list_books(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    books = db.query(models.Book).all()
    result = []
    for book in books:
        ub = db.query(models.UserBook).filter_by(user_id=current_user.id, book_id=book.id).first()
        prog = db.query(models.ReadingProgress).filter_by(user_id=current_user.id, book_id=book.id).first()
        result.append(book_to_response(book, ub, prog))
    return result


@router.get("/books/{book_id}", response_model=BookResponse)
def get_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    book = db.query(models.Book).filter_by(id=book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    ub = db.query(models.UserBook).filter_by(user_id=current_user.id, book_id=book.id).first()
    prog = db.query(models.ReadingProgress).filter_by(user_id=current_user.id, book_id=book.id).first()
    return book_to_response(book, ub, prog)


@router.delete("/books/{book_id}", status_code=204)
def delete_book(
    book_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    book = db.query(models.Book).filter_by(id=book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    # Remove file
    try:
        if os.path.exists(book.file_path):
            os.remove(book.file_path)
    except Exception:
        pass
    db.query(models.UserBook).filter_by(book_id=book_id).delete()
    db.query(models.ReadingProgress).filter_by(book_id=book_id).delete()
    db.query(models.ReadingSession).filter_by(book_id=book_id).delete()
    db.delete(book)
    db.commit()


@router.patch("/books/{book_id}", response_model=BookResponse)
def update_book(
    book_id: int,
    req: BookUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    book = db.query(models.Book).filter_by(id=book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if req.title is not None:
        book.title = req.title
    if req.author is not None:
        book.author = req.author
    if req.genres is not None:
        book.genres = json.dumps(req.genres)

    db.commit()
    db.refresh(book)

    ub = db.query(models.UserBook).filter_by(user_id=current_user.id, book_id=book.id).first()
    prog = db.query(models.ReadingProgress).filter_by(user_id=current_user.id, book_id=book.id).first()
    return book_to_response(book, ub, prog)


@router.post("/books/{book_id}/shelf", response_model=BookResponse)
def update_shelf(
    book_id: int,
    req: ShelfRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    book = db.query(models.Book).filter_by(id=book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    valid_statuses = [s.value for s in models.ShelfStatus]
    if req.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of {valid_statuses}")

    ub = db.query(models.UserBook).filter_by(user_id=current_user.id, book_id=book_id).first()
    if not ub:
        ub = models.UserBook(user_id=current_user.id, book_id=book_id)
        db.add(ub)

    ub.status = models.ShelfStatus(req.status)
    if req.rating is not None:
        ub.rating = req.rating
    if req.status == "reading" and not ub.started_at:
        ub.started_at = datetime.utcnow()
    if req.status == "read" and not ub.finished_at:
        ub.finished_at = datetime.utcnow()

    db.commit()
    db.refresh(ub)

    prog = db.query(models.ReadingProgress).filter_by(user_id=current_user.id, book_id=book_id).first()
    return book_to_response(book, ub, prog)
