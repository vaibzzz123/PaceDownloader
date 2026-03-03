import asyncio
from logging_config import get_logger

logger = get_logger(__name__)


class Broadcaster:
    """
    Distributes events to all connected SSE clients.
    Each subscriber gets its own asyncio.Queue; publish() puts to all of them.
    """

    def __init__(self):
        self._subscribers: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.append(q)
        logger.debug("SSE subscriber added (%d total)", len(self._subscribers))
        return q

    def unsubscribe(self, q: asyncio.Queue):
        try:
            self._subscribers.remove(q)
            logger.debug("SSE subscriber removed (%d remaining)", len(self._subscribers))
        except ValueError:
            pass

    def publish(self, event: dict):
        for q in self._subscribers:
            q.put_nowait(event)
