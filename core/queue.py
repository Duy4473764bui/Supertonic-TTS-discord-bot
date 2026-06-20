"""
core/queue.py - Asyncio-based TTS message queue.

Provides a thin wrapper around :class:`asyncio.Queue` with helpers used by
the voice manager and the message listener cog.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import config

logger = logging.getLogger(__name__)


class TTSQueue:
    """FIFO queue for TTS messages.

    Thread-safety: all methods must be called from the asyncio event loop.
    """

    def __init__(self, maxsize: int = config.QUEUE_MAX_SIZE) -> None:
        self._queue: asyncio.Queue[str] = asyncio.Queue(maxsize=maxsize)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def put(self, text: str) -> bool:
        """Enqueue *text* for TTS playback.

        Returns ``True`` on success, ``False`` if the queue is full.
        """
        try:
            self._queue.put_nowait(text)
            logger.debug("TTSQueue: enqueued message (qsize=%d)", self._queue.qsize())
            return True
        except asyncio.QueueFull:
            logger.warning(
                "TTSQueue: queue is full (%d items); dropping message.", self._queue.qsize()
            )
            return False

    async def get(self) -> str:
        """Dequeue the next message, waiting if necessary."""
        text = await self._queue.get()
        logger.debug("TTSQueue: dequeued message (qsize=%d)", self._queue.qsize())
        return text

    def task_done(self) -> None:
        """Signal that a previously dequeued item has been processed."""
        self._queue.task_done()

    def clear(self) -> int:
        """Drain the queue immediately.

        Returns the number of items that were removed.
        """
        count = 0
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
                count += 1
            except asyncio.QueueEmpty:
                break
        if count:
            logger.info("TTSQueue: cleared %d queued item(s).", count)
        return count

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def size(self) -> int:
        """Current number of items waiting in the queue."""
        return self._queue.qsize()

    @property
    def empty(self) -> bool:
        """``True`` when the queue has no pending items."""
        return self._queue.empty()

    @property
    def full(self) -> bool:
        """``True`` when the queue has reached its capacity."""
        return self._queue.full()

    def peek(self) -> Optional[str]:
        """Return the next item without removing it, or ``None`` if empty.

        .. note::
            :class:`asyncio.Queue` has no native peek; we access the internal
            deque directly.  This is safe from a single-threaded asyncio context.
        """
        try:
            # pylint: disable=protected-access
            return self._queue._queue[0]  # type: ignore[attr-defined]
        except (IndexError, AttributeError):
            return None
