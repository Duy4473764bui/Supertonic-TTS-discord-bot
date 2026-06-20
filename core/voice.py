"""
core/voice.py - Voice connection lifecycle and audio playback management.

Responsibilities
----------------
* Connect to / disconnect from Discord voice channels.
* Drive the FIFO :class:`~core.queue.TTSQueue` — synthesise each message with
  :class:`~core.tts.TTSEngine` and play it via FFmpeg, one at a time.
* Monitor the voice channel for human members; auto-disconnect when empty.
* Clean up temporary WAV files after playback.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import discord

import config
from core.queue import TTSQueue
from core.tts import TTSEngine

logger = logging.getLogger(__name__)


class VoiceManager:
    """Manages one voice connection for the bot.

    One instance is shared across all cogs via the bot's ``voice_manager``
    attribute (set in ``main.py``).

    Lifecycle::

        vm = VoiceManager(bot)
        await vm.connect(voice_channel)
        # … messages arrive and are enqueued via vm.enqueue(text) …
        await vm.disconnect()
    """

    def __init__(self, bot: discord.ext.commands.Bot) -> None:
        self._bot = bot
        self._tts = TTSEngine()
        self._queue = TTSQueue()

        self._voice_client: Optional[discord.VoiceClient] = None
        self._playback_task: Optional[asyncio.Task] = None
        self._monitor_task: Optional[asyncio.Task] = None

        # Event set while a WAV is being played so the playback loop can await it.
        self._playback_finished = asyncio.Event()
        self._is_playing: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        """``True`` when the bot is currently in a voice channel."""
        return self._voice_client is not None and self._voice_client.is_connected()

    @property
    def voice_channel(self) -> Optional[discord.VoiceChannel]:
        """The currently connected voice channel, or ``None``."""
        if self._voice_client and self._voice_client.is_connected():
            return self._voice_client.channel  # type: ignore[return-value]
        return None

    async def connect(self, channel: discord.VoiceChannel) -> bool:
        """Connect to *channel* and start background tasks.

        Returns ``True`` on success.
        """
        if self.is_connected:
            logger.warning(
                "VoiceManager.connect called while already connected to %s.",
                self._voice_client.channel,
            )
            return False

        try:
            logger.info("VoiceManager: connecting to voice channel '%s' …", channel.name)
            self._voice_client = await channel.connect(timeout=10.0, reconnect=True)
            logger.info("VoiceManager: connected to '%s'.", channel.name)
        except (discord.ClientException, asyncio.TimeoutError):
            logger.exception("VoiceManager: failed to connect to '%s'.", channel.name)
            self._voice_client = None
            return False

        self._start_background_tasks()
        return True

    async def disconnect(self) -> None:
        """Stop playback, clear the queue, and leave the voice channel."""
        logger.info("VoiceManager: disconnecting …")

        # Cancel background tasks first so they don't interfere.
        await self._cancel_background_tasks()

        # Stop any active FFmpeg process.
        if self._voice_client and self._voice_client.is_playing():
            self._voice_client.stop()

        self._queue.clear()

        if self._voice_client:
            try:
                await self._voice_client.disconnect(force=True)
            except Exception:
                logger.exception("VoiceManager: error while disconnecting.")
            self._voice_client = None

        self._is_playing = False
        logger.info("VoiceManager: disconnected.")

    async def enqueue(self, text: str) -> bool:
        """Add *text* to the TTS playback queue.

        Returns ``False`` if the bot is not connected or the queue is full.
        """
        if not self.is_connected:
            logger.debug("VoiceManager.enqueue: not connected – ignoring.")
            return False
        return await self._queue.put(text)

    # ------------------------------------------------------------------
    # Background task management
    # ------------------------------------------------------------------

    def _start_background_tasks(self) -> None:
        """Spawn the playback loop and the empty-channel monitor."""
        self._playback_task = asyncio.create_task(
            self._playback_loop(), name="tts-playback-loop"
        )
        self._monitor_task = asyncio.create_task(
            self._monitor_channel(), name="tts-channel-monitor"
        )
        logger.debug("VoiceManager: background tasks started.")

    async def _cancel_background_tasks(self) -> None:
        """Cancel and await the background tasks gracefully."""
        for task in (self._playback_task, self._monitor_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        self._playback_task = None
        self._monitor_task = None

    # ------------------------------------------------------------------
    # Playback loop
    # ------------------------------------------------------------------

    async def _playback_loop(self) -> None:
        """Continuously dequeue messages, synthesise, and play them in order."""
        logger.debug("VoiceManager: playback loop started.")
        try:
            while True:
                text = await self._queue.get()
                try:
                    await self._play_text(text)
                except Exception:
                    logger.exception(
                        "VoiceManager: unhandled error playing message: %r", text[:80]
                    )
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            logger.debug("VoiceManager: playback loop cancelled.")
            raise

    async def _play_text(self, text: str) -> None:
        """Synthesise *text* and block until playback finishes."""
        wav_path: Optional[str] = None
        try:
            wav_path = await self._tts.synthesize(text)
            if wav_path is None:
                logger.warning("VoiceManager: synthesis returned None for: %r", text[:80])
                return

            if not self.is_connected:
                logger.debug("VoiceManager: voice client disconnected before playback.")
                return

            await self._play_wav(wav_path)
        finally:
            # Always clean up the temporary file.
            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                    logger.debug("VoiceManager: removed temp file %s", wav_path)
                except OSError:
                    logger.warning("VoiceManager: could not remove %s", wav_path)

    async def _play_wav(self, wav_path: str) -> None:
        """Play *wav_path* via FFmpeg and wait until it finishes."""
        if not self._voice_client or not self._voice_client.is_connected():
            return

        self._playback_finished.clear()
        self._is_playing = True

        source = discord.FFmpegPCMAudio(
            wav_path,
            executable=config.FFMPEG_PATH,
            options=config.FFMPEG_OPTIONS,
        )

        def _after(error: Optional[Exception]) -> None:
            self._is_playing = False
            if error:
                logger.error("VoiceManager: FFmpeg playback error: %s", error)
            # Signal the awaiting coroutine that playback is done.
            self._bot.loop.call_soon_threadsafe(self._playback_finished.set)

        try:
            self._voice_client.play(source, after=_after)
            logger.debug("VoiceManager: playing %s …", wav_path)
            await self._playback_finished.wait()
            logger.debug("VoiceManager: finished playing %s.", wav_path)
        except discord.ClientException as exc:
            # Already playing – shouldn't happen with a serial queue, but guard anyway.
            logger.error("VoiceManager: discord.ClientException during play: %s", exc)
            self._is_playing = False
            self._playback_finished.set()

    # ------------------------------------------------------------------
    # Empty-channel monitor
    # ------------------------------------------------------------------

    async def _monitor_channel(self) -> None:
        """Periodically check whether the voice channel still has human members.

        Disconnects automatically when no humans remain.
        """
        logger.debug("VoiceManager: channel monitor started.")
        try:
            while True:
                await asyncio.sleep(config.EMPTY_CHANNEL_CHECK_INTERVAL)

                if not self.is_connected:
                    logger.debug("VoiceManager: monitor – no longer connected; stopping.")
                    break

                channel = self.voice_channel
                if channel is None:
                    break

                # Count non-bot members in the channel.
                human_count = sum(
                    1 for m in channel.members if not m.bot
                )

                if human_count == 0:
                    logger.info(
                        "VoiceManager: no humans in '%s'; auto-disconnecting.", channel.name
                    )
                    await self.disconnect()
                    break

        except asyncio.CancelledError:
            logger.debug("VoiceManager: channel monitor cancelled.")
            raise
        except Exception:
            logger.exception("VoiceManager: unexpected error in channel monitor.")
