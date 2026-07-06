from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database import get_db
from auth import get_current_user
import models

router = APIRouter(prefix="/social", tags=["social"])


# ---- Schemas ----

class UserPublic(BaseModel):
    id: int
    username: str

class FriendshipOut(BaseModel):
    id: int
    user: UserPublic
    status: str
    created_at: str

class FriendRequestCreate(BaseModel):
    username: str

class GroupCreate(BaseModel):
    name: str
    book_id: int

class GroupOut(BaseModel):
    id: int
    name: str
    book_id: int
    book_title: str
    creator: str
    member_count: int
    members: list
    created_at: str

class SharedHighlightCreate(BaseModel):
    book_id: int
    cfi_range: str
    text: str
    note: Optional[str] = None
    color: str = "#ffff00"

class SharedHighlightOut(BaseModel):
    id: int
    user: UserPublic
    book_id: int
    cfi_range: str
    text: str
    note: Optional[str]
    color: str
    created_at: str
    comment_count: int

class CommentCreate(BaseModel):
    text: str

class CommentOut(BaseModel):
    id: int
    user: UserPublic
    text: str
    created_at: str

class ClubCreate(BaseModel):
    name: str
    description: Optional[str] = None
    book_id: Optional[int] = None
    target_date: Optional[str] = None

class ClubOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    book_id: Optional[int]
    book_title: Optional[str]
    target_date: Optional[str]
    creator: str
    member_count: int
    members: list
    created_at: str

class DiscussionCreate(BaseModel):
    title: str
    body: Optional[str] = None

class DiscussionOut(BaseModel):
    id: int
    user: UserPublic
    title: str
    body: Optional[str]
    reply_count: int
    created_at: str

class ReplyCreate(BaseModel):
    body: str

class ReplyOut(BaseModel):
    id: int
    user: UserPublic
    body: str
    created_at: str

class NotificationOut(BaseModel):
    id: int
    type: str
    message: str
    link: Optional[str]
    is_read: bool
    created_at: str


def _user_public(user: models.User) -> dict:
    return {"id": user.id, "username": user.username}


def _notify(db: Session, user_id: int, ntype: models.NotificationType, message: str, link: str = None):
    n = models.Notification(user_id=user_id, type=ntype, message=message, link=link)
    db.add(n)


# ===================== FRIENDS =====================

@router.get("/friends", response_model=List[FriendshipOut])
def list_friends(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    friendships = db.query(models.Friendship).filter(
        or_(
            and_(models.Friendship.requester_id == user.id, models.Friendship.status == models.FriendshipStatus.accepted),
            and_(models.Friendship.addressee_id == user.id, models.Friendship.status == models.FriendshipStatus.accepted),
        )
    ).all()

    result = []
    for f in friendships:
        other = f.addressee if f.requester_id == user.id else f.requester
        result.append({
            "id": f.id,
            "user": _user_public(other),
            "status": f.status.value,
            "created_at": f.created_at.isoformat(),
        })
    return result


@router.get("/friends/requests", response_model=List[FriendshipOut])
def list_friend_requests(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    pending = db.query(models.Friendship).filter(
        models.Friendship.addressee_id == user.id,
        models.Friendship.status == models.FriendshipStatus.pending,
    ).all()
    return [{
        "id": f.id,
        "user": _user_public(f.requester),
        "status": f.status.value,
        "created_at": f.created_at.isoformat(),
    } for f in pending]


@router.post("/friends/request", response_model=FriendshipOut)
def send_friend_request(req: FriendRequestCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    target = db.query(models.User).filter(models.User.username == req.username).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")

    existing = db.query(models.Friendship).filter(
        or_(
            and_(models.Friendship.requester_id == user.id, models.Friendship.addressee_id == target.id),
            and_(models.Friendship.requester_id == target.id, models.Friendship.addressee_id == user.id),
        )
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Friend request already exists")

    friendship = models.Friendship(requester_id=user.id, addressee_id=target.id)
    db.add(friendship)
    _notify(db, target.id, models.NotificationType.friend_request, f"{user.username} sent you a friend request", "/social")
    db.commit()
    db.refresh(friendship)

    return {
        "id": friendship.id,
        "user": _user_public(target),
        "status": friendship.status.value,
        "created_at": friendship.created_at.isoformat(),
    }


@router.post("/friends/{friendship_id}/accept")
def accept_friend_request(friendship_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    f = db.query(models.Friendship).filter(
        models.Friendship.id == friendship_id,
        models.Friendship.addressee_id == user.id,
        models.Friendship.status == models.FriendshipStatus.pending,
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Request not found")
    f.status = models.FriendshipStatus.accepted
    _notify(db, f.requester_id, models.NotificationType.friend_accepted, f"{user.username} accepted your friend request", "/social")
    db.commit()
    return {"ok": True}


@router.delete("/friends/{friendship_id}")
def remove_friend(friendship_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    f = db.query(models.Friendship).filter(
        models.Friendship.id == friendship_id,
        or_(models.Friendship.requester_id == user.id, models.Friendship.addressee_id == user.id),
    ).first()
    if not f:
        raise HTTPException(status_code=404, detail="Friendship not found")
    db.delete(f)
    db.commit()
    return {"ok": True}


@router.get("/friends/{user_id}/shelf")
def view_friend_shelf(user_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    # Check they are friends
    is_friend = db.query(models.Friendship).filter(
        models.Friendship.status == models.FriendshipStatus.accepted,
        or_(
            and_(models.Friendship.requester_id == user.id, models.Friendship.addressee_id == user_id),
            and_(models.Friendship.requester_id == user_id, models.Friendship.addressee_id == user.id),
        )
    ).first()
    if not is_friend:
        raise HTTPException(status_code=403, detail="Not friends with this user")

    user_books = db.query(models.UserBook).filter(models.UserBook.user_id == user_id).all()
    result = []
    for ub in user_books:
        prog = db.query(models.ReadingProgress).filter(
            models.ReadingProgress.user_id == user_id,
            models.ReadingProgress.book_id == ub.book_id,
        ).first()
        result.append({
            "book_id": ub.book.id,
            "title": ub.book.title,
            "author": ub.book.author,
            "cover_url": f"/bookworm{ub.book.cover_url}" if ub.book.cover_url else None,
            "status": ub.status.value,
            "progress": prog.percentage if prog else 0,
        })
    return result


# ===================== READING GROUPS =====================

@router.post("/groups", response_model=GroupOut)
def create_group(req: GroupCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    book = db.query(models.Book).filter(models.Book.id == req.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    group = models.ReadingGroup(name=req.name, book_id=req.book_id, created_by=user.id)
    db.add(group)
    db.flush()
    member = models.GroupMember(group_id=group.id, user_id=user.id)
    db.add(member)
    db.commit()
    db.refresh(group)

    return _group_out(group)


def _group_out(group: models.ReadingGroup) -> dict:
    return {
        "id": group.id,
        "name": group.name,
        "book_id": group.book_id,
        "book_title": group.book.title if group.book else "",
        "creator": group.creator.username,
        "member_count": len(group.members),
        "members": [{"id": m.user.id, "username": m.user.username} for m in group.members],
        "created_at": group.created_at.isoformat(),
    }


@router.get("/groups", response_model=List[GroupOut])
def list_groups(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    groups = db.query(models.ReadingGroup).join(models.GroupMember).filter(
        models.GroupMember.user_id == user.id
    ).all()
    return [_group_out(g) for g in groups]


@router.post("/groups/{group_id}/join")
def join_group(group_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    group = db.query(models.ReadingGroup).filter(models.ReadingGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    existing = db.query(models.GroupMember).filter(
        models.GroupMember.group_id == group_id, models.GroupMember.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")
    db.add(models.GroupMember(group_id=group_id, user_id=user.id))
    db.commit()
    return {"ok": True}


@router.post("/groups/{group_id}/leave")
def leave_group(group_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    member = db.query(models.GroupMember).filter(
        models.GroupMember.group_id == group_id, models.GroupMember.user_id == user.id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Not a member")
    db.delete(member)
    db.commit()
    return {"ok": True}


@router.get("/groups/{group_id}/progress")
def group_progress(group_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    group = db.query(models.ReadingGroup).filter(models.ReadingGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    result = []
    for m in group.members:
        prog = db.query(models.ReadingProgress).filter(
            models.ReadingProgress.user_id == m.user_id,
            models.ReadingProgress.book_id == group.book_id,
        ).first()
        result.append({
            "user": _user_public(m.user),
            "percentage": prog.percentage if prog else 0,
        })
    return result


# ===================== SHARED HIGHLIGHTS =====================

@router.post("/highlights", response_model=SharedHighlightOut)
def share_highlight(req: SharedHighlightCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    hl = models.SharedHighlight(
        user_id=user.id, book_id=req.book_id, cfi_range=req.cfi_range,
        text=req.text, note=req.note, color=req.color,
    )
    db.add(hl)
    db.commit()
    db.refresh(hl)
    return _highlight_out(hl)


def _highlight_out(hl: models.SharedHighlight) -> dict:
    return {
        "id": hl.id,
        "user": _user_public(hl.user),
        "book_id": hl.book_id,
        "cfi_range": hl.cfi_range,
        "text": hl.text,
        "note": hl.note,
        "color": hl.color,
        "created_at": hl.created_at.isoformat(),
        "comment_count": len(hl.comments),
    }


@router.get("/highlights/book/{book_id}", response_model=List[SharedHighlightOut])
def list_book_highlights(book_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    highlights = db.query(models.SharedHighlight).filter(models.SharedHighlight.book_id == book_id).order_by(
        models.SharedHighlight.created_at.desc()
    ).all()
    return [_highlight_out(hl) for hl in highlights]


@router.post("/highlights/{highlight_id}/comments", response_model=CommentOut)
def add_comment(highlight_id: int, req: CommentCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    hl = db.query(models.SharedHighlight).filter(models.SharedHighlight.id == highlight_id).first()
    if not hl:
        raise HTTPException(status_code=404, detail="Highlight not found")
    comment = models.HighlightComment(highlight_id=highlight_id, user_id=user.id, text=req.text)
    db.add(comment)
    if hl.user_id != user.id:
        _notify(db, hl.user_id, models.NotificationType.highlight_comment,
                f"{user.username} commented on your highlight", f"/social")
    db.commit()
    db.refresh(comment)
    return {"id": comment.id, "user": _user_public(user), "text": comment.text, "created_at": comment.created_at.isoformat()}


@router.get("/highlights/{highlight_id}/comments", response_model=List[CommentOut])
def list_comments(highlight_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    comments = db.query(models.HighlightComment).filter(
        models.HighlightComment.highlight_id == highlight_id
    ).order_by(models.HighlightComment.created_at.asc()).all()
    return [{"id": c.id, "user": _user_public(c.user), "text": c.text, "created_at": c.created_at.isoformat()} for c in comments]


@router.delete("/highlights/{highlight_id}")
def delete_highlight(highlight_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    hl = db.query(models.SharedHighlight).filter(
        models.SharedHighlight.id == highlight_id, models.SharedHighlight.user_id == user.id
    ).first()
    if not hl:
        raise HTTPException(status_code=404, detail="Highlight not found or not yours")
    db.delete(hl)
    db.commit()
    return {"ok": True}


# ===================== BOOK CLUBS =====================

@router.post("/clubs", response_model=ClubOut)
def create_club(req: ClubCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    target_dt = None
    if req.target_date:
        try:
            target_dt = datetime.fromisoformat(req.target_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")

    club = models.BookClub(
        name=req.name, description=req.description, book_id=req.book_id,
        target_date=target_dt, created_by=user.id,
    )
    db.add(club)
    db.flush()
    db.add(models.ClubMember(club_id=club.id, user_id=user.id))
    db.commit()
    db.refresh(club)
    return _club_out(club)


def _club_out(club: models.BookClub) -> dict:
    return {
        "id": club.id,
        "name": club.name,
        "description": club.description,
        "book_id": club.book_id,
        "book_title": club.book.title if club.book else None,
        "target_date": club.target_date.isoformat() if club.target_date else None,
        "creator": club.creator.username,
        "member_count": len(club.members),
        "members": [{"id": m.user.id, "username": m.user.username} for m in club.members],
        "created_at": club.created_at.isoformat(),
    }


@router.get("/clubs", response_model=List[ClubOut])
def list_clubs(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    clubs = db.query(models.BookClub).join(models.ClubMember).filter(
        models.ClubMember.user_id == user.id
    ).all()
    return [_club_out(c) for c in clubs]


@router.get("/clubs/discover", response_model=List[ClubOut])
def discover_clubs(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """List all clubs (for discovery/joining)."""
    clubs = db.query(models.BookClub).order_by(models.BookClub.created_at.desc()).limit(50).all()
    return [_club_out(c) for c in clubs]


@router.post("/clubs/{club_id}/join")
def join_club(club_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    club = db.query(models.BookClub).filter(models.BookClub.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    existing = db.query(models.ClubMember).filter(
        models.ClubMember.club_id == club_id, models.ClubMember.user_id == user.id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Already a member")
    db.add(models.ClubMember(club_id=club_id, user_id=user.id))
    db.commit()
    return {"ok": True}


@router.post("/clubs/{club_id}/leave")
def leave_club(club_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    member = db.query(models.ClubMember).filter(
        models.ClubMember.club_id == club_id, models.ClubMember.user_id == user.id
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Not a member")
    db.delete(member)
    db.commit()
    return {"ok": True}


@router.delete("/clubs/{club_id}")
def delete_club(club_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    club = db.query(models.BookClub).filter(
        models.BookClub.id == club_id, models.BookClub.created_by == user.id
    ).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found or not owner")
    db.delete(club)
    db.commit()
    return {"ok": True}


# ---- Club Discussions ----

@router.post("/clubs/{club_id}/discussions", response_model=DiscussionOut)
def create_discussion(club_id: int, req: DiscussionCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    club = db.query(models.BookClub).filter(models.BookClub.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    disc = models.Discussion(club_id=club_id, user_id=user.id, title=req.title, body=req.body)
    db.add(disc)
    # Notify other members
    for m in club.members:
        if m.user_id != user.id:
            _notify(db, m.user_id, models.NotificationType.club_discussion,
                    f"{user.username} posted in {club.name}: {req.title}", "/social")
    db.commit()
    db.refresh(disc)
    return _discussion_out(disc)


def _discussion_out(d: models.Discussion) -> dict:
    return {
        "id": d.id,
        "user": _user_public(d.user),
        "title": d.title,
        "body": d.body,
        "reply_count": len(d.replies),
        "created_at": d.created_at.isoformat(),
    }


@router.get("/clubs/{club_id}/discussions", response_model=List[DiscussionOut])
def list_discussions(club_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    discussions = db.query(models.Discussion).filter(
        models.Discussion.club_id == club_id
    ).order_by(models.Discussion.created_at.desc()).all()
    return [_discussion_out(d) for d in discussions]


@router.post("/discussions/{discussion_id}/replies", response_model=ReplyOut)
def add_reply(discussion_id: int, req: ReplyCreate, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    disc = db.query(models.Discussion).filter(models.Discussion.id == discussion_id).first()
    if not disc:
        raise HTTPException(status_code=404, detail="Discussion not found")
    reply = models.DiscussionReply(discussion_id=discussion_id, user_id=user.id, body=req.body)
    db.add(reply)
    if disc.user_id != user.id:
        _notify(db, disc.user_id, models.NotificationType.club_discussion,
                f"{user.username} replied to your discussion: {disc.title}", "/social")
    db.commit()
    db.refresh(reply)
    return {"id": reply.id, "user": _user_public(user), "body": reply.body, "created_at": reply.created_at.isoformat()}


@router.get("/discussions/{discussion_id}/replies", response_model=List[ReplyOut])
def list_replies(discussion_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    replies = db.query(models.DiscussionReply).filter(
        models.DiscussionReply.discussion_id == discussion_id
    ).order_by(models.DiscussionReply.created_at.asc()).all()
    return [{"id": r.id, "user": _user_public(r.user), "body": r.body, "created_at": r.created_at.isoformat()} for r in replies]


# ===================== NOTIFICATIONS =====================

@router.get("/notifications", response_model=List[NotificationOut])
def list_notifications(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    notifs = db.query(models.Notification).filter(
        models.Notification.user_id == user.id
    ).order_by(models.Notification.created_at.desc()).limit(50).all()
    return [{
        "id": n.id, "type": n.type.value, "message": n.message,
        "link": n.link, "is_read": n.is_read, "created_at": n.created_at.isoformat(),
    } for n in notifs]


@router.get("/notifications/unread-count")
def unread_count(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    count = db.query(models.Notification).filter(
        models.Notification.user_id == user.id, models.Notification.is_read == False
    ).count()
    return {"count": count}


@router.post("/notifications/read-all")
def mark_all_read(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    db.query(models.Notification).filter(
        models.Notification.user_id == user.id, models.Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"ok": True}


@router.post("/notifications/{notification_id}/read")
def mark_read(notification_id: int, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    n = db.query(models.Notification).filter(
        models.Notification.id == notification_id, models.Notification.user_id == user.id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    n.is_read = True
    db.commit()
    return {"ok": True}


# ===================== USER SEARCH =====================

@router.get("/users/search")
def search_users(q: str = "", db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    if len(q) < 2:
        return []
    users = db.query(models.User).filter(
        models.User.username.ilike(f"%{q}%"),
        models.User.id != user.id,
        models.User.is_active == True,
    ).limit(20).all()
    return [_user_public(u) for u in users]


# ===================== ACTIVITY FEED =====================

@router.get("/feed")
def activity_feed(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Get recent activity from friends."""
    # Get friend IDs
    friendships = db.query(models.Friendship).filter(
        models.Friendship.status == models.FriendshipStatus.accepted,
        or_(models.Friendship.requester_id == user.id, models.Friendship.addressee_id == user.id),
    ).all()
    friend_ids = set()
    for f in friendships:
        friend_ids.add(f.addressee_id if f.requester_id == user.id else f.requester_id)

    if not friend_ids:
        return []

    # Recent book completions by friends
    feed = []
    completed = db.query(models.UserBook).filter(
        models.UserBook.user_id.in_(friend_ids),
        models.UserBook.status == models.ShelfStatus.read,
        models.UserBook.finished_at.isnot(None),
    ).order_by(models.UserBook.finished_at.desc()).limit(20).all()

    for ub in completed:
        feed.append({
            "type": "book_finished",
            "user": _user_public(ub.user),
            "book_title": ub.book.title,
            "book_id": ub.book.id,
            "cover_url": f"/bookworm{ub.book.cover_url}" if ub.book.cover_url else None,
            "timestamp": ub.finished_at.isoformat() if ub.finished_at else ub.added_at.isoformat(),
        })

    # Recent shared highlights by friends
    highlights = db.query(models.SharedHighlight).filter(
        models.SharedHighlight.user_id.in_(friend_ids),
    ).order_by(models.SharedHighlight.created_at.desc()).limit(20).all()

    for hl in highlights:
        feed.append({
            "type": "shared_highlight",
            "user": _user_public(hl.user),
            "book_id": hl.book_id,
            "book_title": hl.book.title if hl.book else "",
            "text": hl.text[:200],
            "timestamp": hl.created_at.isoformat(),
        })

    # Sort by timestamp desc
    feed.sort(key=lambda x: x["timestamp"], reverse=True)
    return feed[:30]
