import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from database import init_db
from routers import users, books, reader, progress, search, analytics, social

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.getenv("DATA_PATH", "/data")
BACKUP_PATH = os.getenv("BACKUP_PATH", "/backups")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initialising database and directories...")
    init_db()

    # Schedule daily backup at 2am
    from services.backup import backup_now

    scheduler.add_job(
        lambda: backup_now(DATA_PATH, BACKUP_PATH),
        CronTrigger(hour=2, minute=0),
        id="daily_backup",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started (daily backup at 02:00)")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)


app = FastAPI(title="Bookworm API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(users.router, prefix="/api")
app.include_router(books.router, prefix="/api")
app.include_router(reader.router, prefix="/api")
app.include_router(progress.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(social.router, prefix="/api")

# Serve cover images as static files
covers_path = f"{DATA_PATH}/covers"
os.makedirs(covers_path, exist_ok=True)
app.mount("/covers", StaticFiles(directory=covers_path), name="covers")


@app.get("/api/health")
def health():
    return {"status": "ok"}
