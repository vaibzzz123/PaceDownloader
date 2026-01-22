"""FastAPI route handlers."""

from routes.episodes import router as episodes_router
from routes.downloads import router as downloads_router
from routes.torrents import router as torrents_router
from routes.settings import router as settings_router

__all__ = [
    "episodes_router",
    "downloads_router",
    "torrents_router",
    "settings_router",
]
