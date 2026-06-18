import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATA_PATH = os.getenv("DATA_PATH", "/data")
os.makedirs(DATA_PATH, exist_ok=True)

DATABASE_URL = f"sqlite:///{os.path.join(DATA_PATH, 'taplord.db')}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    import models  # noqa: F401 — ensure all models are loaded
    Base.metadata.create_all(bind=engine)
