from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
import enum

from database import Base


class ShelfStatus(str, enum.Enum):
    backlog = "backlog"
    reading = "reading"
    read = "read"


class FileType(str, enum.Enum):
    epub = "epub"
    pdf = "pdf"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    user_books = relationship("UserBook", back_populates="user")
    reading_sessions = relationship("ReadingSession", back_populates="user")
    reading_progress = relationship("ReadingProgress", back_populates="user")


class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False, index=True)
    author = Column(String(512), nullable=True)
    isbn = Column(String(20), nullable=True)
    cover_url = Column(String(1024), nullable=True)
    file_path = Column(String(1024), nullable=False)
    file_type = Column(Enum(FileType), nullable=False)
    total_pages = Column(Integer, nullable=True)
    total_words = Column(Integer, nullable=True)
    genres = Column(Text, nullable=True)  # JSON-encoded list
    added_at = Column(DateTime, default=datetime.utcnow)
    added_by = Column(Integer, ForeignKey("users.id"), nullable=True)

    user_books = relationship("UserBook", back_populates="book")
    reading_sessions = relationship("ReadingSession", back_populates="book")
    reading_progress = relationship("ReadingProgress", back_populates="book")


class UserBook(Base):
    __tablename__ = "user_books"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    status = Column(Enum(ShelfStatus), default=ShelfStatus.backlog, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    rating = Column(Integer, nullable=True)  # 1-5

    user = relationship("User", back_populates="user_books")
    book = relationship("Book", back_populates="user_books")


class ReadingSession(Base):
    __tablename__ = "reading_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=False)
    start_position = Column(String(512), nullable=True)
    end_position = Column(String(512), nullable=True)
    words_read = Column(Integer, default=0)
    pages_read = Column(Integer, default=0)

    user = relationship("User", back_populates="reading_sessions")
    book = relationship("Book", back_populates="reading_sessions")


class ReadingProgress(Base):
    __tablename__ = "reading_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    position = Column(String(512), nullable=True)  # CFI for epub, page number for pdf
    percentage = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="reading_progress")
    book = relationship("Book", back_populates="reading_progress")
