import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler

from database import init_db, DATA_PATH
from services.auto_end import auto_end_stale_events

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()

    # Ensure covers directory exists for static file serving
    covers_dir = os.path.join(DATA_PATH, "covers")
    os.makedirs(covers_dir, exist_ok=True)

    # Start background scheduler for auto-ending stale events
    scheduler.add_job(auto_end_stale_events, "interval", minutes=30, id="auto_end")
    scheduler.start()
    print("[taplord] Background scheduler started")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    print("[taplord] Background scheduler stopped")


app = FastAPI(
    title="Taplord API",
    description="Competitive beer tracking API",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file serving for uploaded covers/photos
covers_dir = os.path.join(DATA_PATH, "covers")
os.makedirs(covers_dir, exist_ok=True)
app.mount("/covers", StaticFiles(directory=covers_dir), name="covers")

# Import and include routers
from routers.users import router as users_router
from routers.events import router as events_router
from routers.checkins import router as checkins_router
from routers.beers import router as beers_router
from routers.leaderboard import router as leaderboard_router

app.include_router(users_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(checkins_router, prefix="/api")
app.include_router(beers_router, prefix="/api")
app.include_router(leaderboard_router, prefix="/api")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "taplord"}
