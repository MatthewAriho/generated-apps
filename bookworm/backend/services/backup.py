import shutil
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)


def backup_now(data_path: str, backup_path: str) -> None:
    today = date.today().isoformat()
    dest = Path(backup_path) / today
    dest.mkdir(parents=True, exist_ok=True)

    # Backup database directory
    db_src = Path(data_path) / "db"
    if db_src.exists():
        db_dest = dest / "db"
        if db_dest.exists():
            shutil.rmtree(db_dest)
        shutil.copytree(str(db_src), str(db_dest))
        logger.info(f"Backed up db to {db_dest}")

    # Backup books directory
    books_src = Path(data_path) / "books"
    if books_src.exists():
        books_dest = dest / "books"
        if books_dest.exists():
            shutil.rmtree(books_dest)
        shutil.copytree(str(books_src), str(books_dest))
        logger.info(f"Backed up books to {books_dest}")

    logger.info(f"Backup complete → {dest}")
