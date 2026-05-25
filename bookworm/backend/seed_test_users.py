"""
Seed script: creates test users, friend connections, book clubs, and sample data.
Run from the backend directory:  python seed_test_users.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import SessionLocal, init_db
import models
import bcrypt

def hash_password(pw: str) -> str:
    return bcrypt.hashpw(pw[:72].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
from datetime import datetime, timedelta

init_db()
db = SessionLocal()

TEST_USERS = [
    ("alice", "password123", "alice@test.com"),
    ("bob", "password123", "bob@test.com"),
    ("charlie", "password123", "charlie@test.com"),
    ("diana", "password123", "diana@test.com"),
    ("eve", "password123", "eve@test.com"),
]

created_users = []

for username, password, email in TEST_USERS:
    existing = db.query(models.User).filter(models.User.username == username).first()
    if existing:
        print(f"  User '{username}' already exists (id={existing.id}), skipping")
        created_users.append(existing)
        continue
    user = models.User(
        username=username,
        email=email,
        hashed_password=hash_password(password),
    )
    db.add(user)
    db.flush()
    created_users.append(user)
    print(f"  Created user '{username}' (id={user.id})")

db.commit()

alice, bob, charlie, diana, eve = created_users

# ---- Friend connections ----
def add_friendship(u1, u2, accepted=True):
    existing = db.query(models.Friendship).filter(
        ((models.Friendship.requester_id == u1.id) & (models.Friendship.addressee_id == u2.id)) |
        ((models.Friendship.requester_id == u2.id) & (models.Friendship.addressee_id == u1.id))
    ).first()
    if existing:
        return
    status = models.FriendshipStatus.accepted if accepted else models.FriendshipStatus.pending
    f = models.Friendship(requester_id=u1.id, addressee_id=u2.id, status=status)
    db.add(f)
    print(f"  Friendship: {u1.username} <-> {u2.username} ({status.value})")

add_friendship(alice, bob)
add_friendship(alice, charlie)
add_friendship(bob, diana)
add_friendship(charlie, diana)
add_friendship(eve, alice, accepted=False)  # pending request from eve to alice
db.commit()

# ---- Sample books (if none exist) ----
book_count = db.query(models.Book).count()
sample_books = []
if book_count == 0:
    books_data = [
        ("The Great Gatsby", "F. Scott Fitzgerald", "epub", '["fiction","classic"]'),
        ("Dune", "Frank Herbert", "epub", '["scifi","fiction"]'),
        ("Sapiens", "Yuval Noah Harari", "epub", '["nonfiction","history"]'),
        ("Project Hail Mary", "Andy Weir", "epub", '["scifi","fiction"]'),
        ("Atomic Habits", "James Clear", "epub", '["nonfiction","self-help"]'),
    ]
    for title, author, ft, genres in books_data:
        b = models.Book(
            title=title, author=author, file_path=f"/data/books/placeholder_{title.lower().replace(' ','_')}.epub",
            file_type=models.FileType.epub, genres=genres, added_by=alice.id,
        )
        db.add(b)
        db.flush()
        sample_books.append(b)
        print(f"  Created book: {title} (id={b.id})")
    db.commit()
else:
    sample_books = db.query(models.Book).limit(5).all()
    print(f"  Using {len(sample_books)} existing books")

# ---- User books & progress ----
def add_user_book(user, book, status, pct=0.0):
    existing = db.query(models.UserBook).filter(
        models.UserBook.user_id == user.id, models.UserBook.book_id == book.id
    ).first()
    if existing:
        return
    ub = models.UserBook(
        user_id=user.id, book_id=book.id,
        status=models.ShelfStatus(status),
        started_at=datetime.utcnow() - timedelta(days=14),
        finished_at=datetime.utcnow() - timedelta(days=2) if status == "read" else None,
    )
    db.add(ub)
    prog = models.ReadingProgress(user_id=user.id, book_id=book.id, percentage=pct)
    db.add(prog)

if len(sample_books) >= 5:
    add_user_book(alice, sample_books[0], "read", 1.0)
    add_user_book(alice, sample_books[1], "reading", 0.45)
    add_user_book(alice, sample_books[2], "backlog", 0.0)
    add_user_book(bob, sample_books[0], "reading", 0.72)
    add_user_book(bob, sample_books[3], "read", 1.0)
    add_user_book(bob, sample_books[4], "backlog", 0.0)
    add_user_book(charlie, sample_books[1], "reading", 0.30)
    add_user_book(charlie, sample_books[2], "read", 1.0)
    add_user_book(diana, sample_books[0], "read", 1.0)
    add_user_book(diana, sample_books[3], "reading", 0.55)
    add_user_book(eve, sample_books[4], "reading", 0.20)
    db.commit()
    print("  Added user books & progress")

# ---- Book Club ----
existing_club = db.query(models.BookClub).filter(models.BookClub.name == "Sci-Fi Sundays").first()
if not existing_club and len(sample_books) >= 4:
    club = models.BookClub(
        name="Sci-Fi Sundays",
        description="We read one sci-fi book a month and discuss it.",
        book_id=sample_books[3].id,
        target_date=datetime.utcnow() + timedelta(days=21),
        created_by=bob.id,
    )
    db.add(club)
    db.flush()
    for u in [bob, alice, charlie]:
        db.add(models.ClubMember(club_id=club.id, user_id=u.id))

    # Add a discussion
    disc = models.Discussion(
        club_id=club.id, user_id=bob.id,
        title="Thoughts on the first 100 pages?",
        body="I'm really hooked by the premise. What does everyone think so far?",
    )
    db.add(disc)
    db.flush()
    db.add(models.DiscussionReply(
        discussion_id=disc.id, user_id=alice.id,
        body="Loving it! The science is so well researched.",
    ))
    db.add(models.DiscussionReply(
        discussion_id=disc.id, user_id=charlie.id,
        body="I'm only on page 50 but it's great so far.",
    ))
    db.commit()
    print(f"  Created book club 'Sci-Fi Sundays' with discussion")

# ---- Another club ----
existing_club2 = db.query(models.BookClub).filter(models.BookClub.name == "Classics Corner").first()
if not existing_club2 and len(sample_books) >= 1:
    club2 = models.BookClub(
        name="Classics Corner",
        description="Revisiting the literary classics, one book at a time.",
        book_id=sample_books[0].id,
        created_by=diana.id,
    )
    db.add(club2)
    db.flush()
    for u in [diana, alice]:
        db.add(models.ClubMember(club_id=club2.id, user_id=u.id))
    db.commit()
    print(f"  Created book club 'Classics Corner'")

# ---- Shared Highlights ----
if len(sample_books) >= 2:
    existing_hl = db.query(models.SharedHighlight).count()
    if existing_hl == 0:
        hl1 = models.SharedHighlight(
            user_id=bob.id, book_id=sample_books[0].id,
            cfi_range="epubcfi(/6/4!/4/2/1:0)", text="So we beat on, boats against the current, borne back ceaselessly into the past.",
            note="What a closing line.", color="#ffff00",
        )
        db.add(hl1)
        db.flush()
        db.add(models.HighlightComment(highlight_id=hl1.id, user_id=alice.id, text="One of the best endings in literature."))

        hl2 = models.SharedHighlight(
            user_id=charlie.id, book_id=sample_books[1].id,
            cfi_range="epubcfi(/6/8!/4/2/1:0)", text="Fear is the mind-killer.",
            note="The Litany Against Fear", color="#90ee90",
        )
        db.add(hl2)
        db.commit()
        print("  Added shared highlights & comments")

# ---- Notifications ----
existing_notifs = db.query(models.Notification).filter(models.Notification.user_id == alice.id).count()
if existing_notifs == 0:
    notifs = [
        (alice.id, models.NotificationType.friend_request, f"{eve.username} sent you a friend request", "/social"),
        (alice.id, models.NotificationType.club_discussion, f"{bob.username} posted in Sci-Fi Sundays: Thoughts on the first 100 pages?", "/social"),
        (alice.id, models.NotificationType.highlight_comment, f"{bob.username} shared a highlight in The Great Gatsby", "/social"),
        (bob.id, models.NotificationType.friend_accepted, f"{alice.username} accepted your friend request", "/social"),
        (charlie.id, models.NotificationType.book_finished, f"{diana.username} finished reading The Great Gatsby", "/social"),
    ]
    for uid, ntype, msg, link in notifs:
        db.add(models.Notification(user_id=uid, type=ntype, message=msg, link=link))
    db.commit()
    print("  Added sample notifications")

# ---- Reading sessions (for feed) ----
existing_sessions = db.query(models.ReadingSession).count()
if existing_sessions == 0 and len(sample_books) >= 4:
    sessions = [
        (alice.id, sample_books[0].id, 7, 45),
        (alice.id, sample_books[1].id, 1, 30),
        (bob.id, sample_books[0].id, 3, 60),
        (bob.id, sample_books[3].id, 5, 40),
        (charlie.id, sample_books[1].id, 2, 25),
        (diana.id, sample_books[0].id, 6, 50),
    ]
    for uid, bid, days_ago, mins in sessions:
        start = datetime.utcnow() - timedelta(days=days_ago, hours=2)
        end = start + timedelta(minutes=mins)
        db.add(models.ReadingSession(
            user_id=uid, book_id=bid,
            started_at=start, ended_at=end,
            words_read=mins * 250, pages_read=mins // 2,
        ))
    db.commit()
    print("  Added reading sessions")

db.close()
print("\nDone! Test accounts (all passwords: password123):")
print("  alice, bob, charlie, diana, eve")
print("\nFriendships: alice<->bob, alice<->charlie, bob<->diana, charlie<->diana")
print("Pending request: eve -> alice")
print("Clubs: 'Sci-Fi Sundays' (bob, alice, charlie), 'Classics Corner' (diana, alice)")
