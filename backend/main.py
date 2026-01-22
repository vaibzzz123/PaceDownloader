"""FastAPI application entry point for One Pace Download Manager."""

import asyncio
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import get_settings, initialize_db
from logging_config import get_logger, setup_logging

# Initialize database and logging before other imports that may log
initialize_db()
settings = get_settings()
log_level = settings["log_level"]["value"] if settings else "INFO"
setup_logging(log_level)

logger = get_logger(__name__)

from routes import (
    episodes_router,
    downloads_router,
    torrents_router,
    settings_router,
)

# Background task handle
_monitor_task: asyncio.Task | None = None


async def monitor_download_completion():
    """
    Background task to monitor download completion.

    Runs at interval configured by qbt_polling_rate setting.
    Checks all episodes with status "downloading" and triggers
    completion handling when files are done.
    """
    from dependencies import get_download_manager, get_settings_repo, get_episode_download_repo

    logger.info("Starting download completion monitor")

    while True:
        try:
            settings_repo = get_settings_repo()
            settings = settings_repo.get_settings()
            polling_rate = settings["qbt_polling_rate"]["value"] if settings else 10

            episode_repo = get_episode_download_repo()
            download_manager = get_download_manager()

            # Get all downloading episodes
            downloading = episode_repo.get_by_status("downloading")

            for episode in downloading:
                _, is_complete = download_manager.check_episode_progress(episode.ep_id)

                if is_complete:
                    logger.info(
                        "Episode %d download complete, creating destination file",
                        episode.ep_id,
                    )
                    result = download_manager.handle_download_complete(episode.ep_id)
                    if result.success:
                        logger.info("Episode %d: %s", episode.ep_id, result.message)
                    else:
                        logger.error("Episode %d: %s", episode.ep_id, result.message)

            await asyncio.sleep(polling_rate)

        except Exception as e:
            logger.error("Error in download monitor: %s", e)
            await asyncio.sleep(10)  # Wait before retrying on error


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan handler."""
    global _monitor_task

    logger.info("Starting One Pace Download Manager API")

    # Start background monitor task
    _monitor_task = asyncio.create_task(monitor_download_completion())

    yield

    # Cleanup on shutdown
    logger.info("Shutting down API")
    if _monitor_task:
        _monitor_task.cancel()
        try:
            await _monitor_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="One Pace Download Manager",
    description="API for managing One Pace episode downloads via qBittorrent",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware - configure appropriately for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(episodes_router, prefix="/api/episodes", tags=["Episodes"])
app.include_router(downloads_router, prefix="/api/downloads", tags=["Downloads"])
app.include_router(torrents_router, prefix="/api/torrents", tags=["Torrents"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "name": "One Pace Download Manager",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_includes=["*.py"],
    )
