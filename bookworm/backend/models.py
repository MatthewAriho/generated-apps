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


class FriendshipStatus(str, enum.Enum):
    pending = "pending"
    accepted = "accepted"


class Friendship(Base):
    __tablename__ = "friendships"

    id = Column(Integer, primary_key=True, index=True)
    requester_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    addressee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(FriendshipStatus), default=FriendshipStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    requester = relationship("User", foreign_keys=[requester_id], backref="sent_requests")
    addressee = relationship("User", foreign_keys=[addressee_id], backref="received_requests")


class ReadingGroup(Base):
    __tablename__ = "reading_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    book = relationship("Book")
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("reading_groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    group = relationship("ReadingGroup", back_populates="members")
    user = relationship("User")


class SharedHighlight(Base):
    __tablename__ = "shared_highlights"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    cfi_range = Column(String(1024), nullable=False)
    text = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    color = Column(String(32), default="#ffff00")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    book = relationship("Book")
    comments = relationship("HighlightComment", back_populates="highlight", cascade="all, delete-orphan")


class HighlightComment(Base):
    __tablename__ = "highlight_comments"

    id = Column(Integer, primary_key=True, index=True)
    highlight_id = Column(Integer, ForeignKey("shared_highlights.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    highlight = relationship("SharedHighlight", back_populates="comments")
    user = relationship("User")


class BookClub(Base):
    __tablename__ = "book_clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    book_id = Column(Integer, ForeignKey("books.id"), nullable=True)
    target_date = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    book = relationship("Book")
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship("ClubMember", back_populates="club", cascade="all, delete-orphan")
    discussions = relationship("Discussion", back_populates="club", cascade="all, delete-orphan")


class ClubMember(Base):
    __tablename__ = "club_members"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("book_clubs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    club = relationship("BookClub", back_populates="members")
    user = relationship("User")


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("book_clubs.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(512), nullable=False)
    body = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    club = relationship("BookClub", back_populates="discussions")
    user = relationship("User")
    replies = relationship("DiscussionReply", back_populates="discussion", cascade="all, delete-orphan")


class DiscussionReply(Base):
    __tablename__ = "discussion_replies"

    id = Column(Integer, primary_key=True, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    discussion = relationship("Discussion", back_populates="replies")
    user = relationship("User")


class NotificationType(str, enum.Enum):
    friend_request = "friend_request"
    friend_accepted = "friend_accepted"
    group_invite = "group_invite"
    club_invite = "club_invite"
    club_discussion = "club_discussion"
    highlight_comment = "highlight_comment"
    book_finished = "book_finished"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(NotificationType), nullable=False)
    message = Column(Text, nullable=False)
    link = Column(String(512), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
