"""Seed script: creates test users, beers, events, check-ins, and a group."""

import os
import random
from datetime import datetime, timedelta

os.environ.setdefault("DATA_PATH", "/data")

from database import SessionLocal, init_db
from auth import hash_password
from models import User, Beer, Event, CheckIn, Group, GroupMember, EventType

init_db()
db = SessionLocal()

# ── Users ──────────────────────────────────────────────────

USERS = [
    ("matty", "Matty B", "#FF6B00", "password123"),
    ("davo", "Davo", "#4CAF50", "password123"),
    ("shazza", "Shazza", "#E91E63", "password123"),
    ("bazza", "Bazza", "#2196F3", "password123"),
    ("tommo", "Tommo", "#9C27B0", "password123"),
    ("richo", "Richo", "#FF9800", "password123"),
]

users = []
for username, display_name, color, pw in USERS:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        users.append(existing)
        continue
    u = User(
        username=username,
        display_name=display_name,
        avatar_color=color,
        hashed_password=hash_password(pw),
        created_at=datetime.utcnow() - timedelta(days=random.randint(10, 60)),
    )
    db.add(u)
    db.flush()
    users.append(u)

db.commit()
print(f"✓ {len(users)} users (password: password123)")

# ── Beers ──────────────────────────────────────────────────

BEERS = [
    ("VB", "Carlton & United", "Lager", 4.9),
    ("Coopers Pale Ale", "Coopers", "Pale Ale", 4.5),
    ("Stone & Wood Pacific Ale", "Stone & Wood", "Pacific Ale", 4.4),
    ("Balter XPA", "Balter", "XPA", 5.0),
    ("Young Henrys Newtowner", "Young Henrys", "Pale Ale", 4.8),
    ("Carlton Draught", "Carlton & United", "Lager", 4.6),
    ("Little Creatures Pale Ale", "Little Creatures", "Pale Ale", 5.2),
    ("4 Pines Pacific Ale", "4 Pines", "Pacific Ale", 3.5),
    ("Pirate Life IPA", "Pirate Life", "IPA", 6.8),
    ("Gage Roads Single Fin", "Gage Roads", "Summer Ale", 4.5),
    ("James Squire 150 Lashes", "James Squire", "Pale Ale", 4.2),
    ("Furphy Refreshing Ale", "Furphy", "Ale", 4.4),
    ("Great Northern", "Carlton & United", "Lager", 4.2),
    ("Guinness Draught", "Guinness", "Stout", 4.2),
    ("Sierra Nevada Pale Ale", "Sierra Nevada", "Pale Ale", 5.6),
    ("Hazy Jane", "BrewDog", "Hazy IPA", 5.0),
]

beers = []
for name, brewery, style, abv in BEERS:
    existing = db.query(Beer).filter(Beer.name == name, Beer.brewery == brewery).first()
    if existing:
        beers.append(existing)
        continue
    b = Beer(
        name=name,
        brewery=brewery,
        style=style,
        abv=abv,
        created_by=users[0].id,
        verified=random.random() > 0.3,
    )
    db.add(b)
    db.flush()
    beers.append(b)

db.commit()
print(f"✓ {len(beers)} beers")

# ── Events & Check-ins ────────────────────────────────────

EVENT_TEMPLATES = [
    ("Friday Sesh", EventType.night_out, "The Local Pub"),
    ("Pub Crawl Madness", EventType.pub_crawl, "CBD"),
    ("Sunday Arvo", EventType.day_drinking, "Backyard"),
    ("Beer Run", EventType.beer_run, None),
    ("Big Night", EventType.night_out, "King Street"),
    ("Crafty Afternoon", EventType.day_drinking, "Craft Bar"),
    ("Tuesday Tinnies", EventType.custom, "Home"),
    ("Grand Final Day", EventType.day_drinking, "Sports Bar"),
]

SIZES = [285, 330, 375, 425, 500, 568]
now = datetime.utcnow()
total_events = 0
total_checkins = 0

for user in users:
    # Each user gets 3-6 past events
    num_events = random.randint(3, 6)
    for i in range(num_events):
        template = random.choice(EVENT_TEMPLATES)
        days_ago = random.randint(1, 45)
        start = now - timedelta(days=days_ago, hours=random.randint(12, 20))
        duration_hours = random.uniform(2, 8)
        end = start + timedelta(hours=duration_hours)

        blacked_out = random.random() < 0.12
        vomited = random.random() < 0.08

        ev = Event(
            user_id=user.id,
            name=template[0],
            event_type=template[1],
            started_at=start,
            ended_at=end,
            is_active=False,
            blacked_out=blacked_out,
            vomited=vomited,
            venue_description=template[2],
        )
        db.add(ev)
        db.flush()
        total_events += 1

        # 2-10 check-ins per event
        num_checkins = random.randint(2, 10)
        for j in range(num_checkins):
            beer = random.choice(beers)
            checkin_time = start + timedelta(
                minutes=random.randint(0, int(duration_hours * 60))
            )
            ci = CheckIn(
                event_id=ev.id,
                user_id=user.id,
                beer_id=beer.id,
                beer_name=beer.name,
                beer_style=beer.style,
                brewery=beer.brewery,
                size_ml=random.choice(SIZES),
                rating=random.choice([None, None, 3, 4, 5, 4, 3, 5]),
                notes=random.choice([None, None, None, "Solid", "Crispy", "Not bad", "Goes down easy", "Bit warm"]),
                created_at=checkin_time,
            )
            db.add(ci)
            total_checkins += 1

db.commit()
print(f"✓ {total_events} events, {total_checkins} check-ins")

# Give matty an active event right now
active = Event(
    user_id=users[0].id,
    name="Live Session",
    event_type=EventType.night_out,
    started_at=now - timedelta(hours=1),
    ended_at=None,
    is_active=True,
    venue_description="The Taphouse",
)
db.add(active)
db.flush()

for k in range(3):
    beer = random.choice(beers[:6])
    ci = CheckIn(
        event_id=active.id,
        user_id=users[0].id,
        beer_id=beer.id,
        beer_name=beer.name,
        beer_style=beer.style,
        brewery=beer.brewery,
        size_ml=random.choice([375, 425, 568]),
        rating=random.choice([4, 5]),
        created_at=now - timedelta(minutes=random.randint(5, 55)),
    )
    db.add(ci)

db.commit()
print("✓ Active event for matty with 3 check-ins")

# ── Group ──────────────────────────────────────────────────

existing_group = db.query(Group).filter(Group.name == "The Legends").first()
if not existing_group:
    group = Group(name="The Legends", created_by=users[0].id)
    db.add(group)
    db.flush()
    for u in users[:4]:
        db.add(GroupMember(group_id=group.id, user_id=u.id))
    db.commit()
    print("✓ Group 'The Legends' (matty, davo, shazza, bazza)")
else:
    print("✓ Group 'The Legends' already exists")

db.close()
print("\n🍺 Seed complete! All users: password123")
