import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATA_PATH = os.getenv("DATA_PATH", "/data")

DATABASE_URL = f"sqlite:///{DATA_PATH}/db/main.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
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
    from models import Base as ModelBase  # noqa: F401 — ensures models are imported
    # Ensure data directories exist
    for directory in ["db", "books", "covers"]:
        Path(f"{DATA_PATH}/{directory}").mkdir(parents=True, exist_ok=True)
    Path(os.getenv("BACKUP_PATH", "/backups")).mkdir(parents=True, exist_ok=True)
    ModelBase.metadata.create_all(bind=engine)
