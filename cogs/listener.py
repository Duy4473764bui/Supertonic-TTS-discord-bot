"""
cogs/listener.py - Message listener cog.

Watches the configured text channel and enqueues every new (non-bot,
non-webhook) message into the shared :class:`~core.voice.VoiceManager`
for TTS playback.
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
from core.utils import sanitise_for_tts
from core.voice import VoiceManager

logger = logging.getLogger(__name__)


class ListenerCog(commands.Cog, name="Listener"):
    """Cog that listens to the configured text channel and feeds the TTS queue."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # ------------------------------------------------------------------
    # Property helpers
    # ------------------------------------------------------------------

    @property
    def _voice_manager(self) -> VoiceManager:
        """Convenience accessor for the shared :class:`VoiceManager`."""
        return self.bot.voice_manager  # type: ignore[attr-defined]

    # ------------------------------------------------------------------
    # Event listeners
    # ------------------------------------------------------------------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Enqueue a message for TTS playback when appropriate.

        Filtering rules (all must pass):
        - Message is in the configured text channel.
        - Author is not a bot.
        - Message was not sent by a webhook.
        - The bot is currently connected to a voice channel.
        - The sanitised text is non-empty.
        """
        # 1. Channel filter – ignore every other channel.
        if message.channel.id != config.TEXT_CHANNEL_ID:
            return

        # 2. Bot filter.
        if message.author.bot:
            logger.debug("ListenerCog: ignoring bot message from %s.", message.author)
            return

        # 3. Webhook filter.
        if message.webhook_id is not None:
            logger.debug("ListenerCog: ignoring webhook message (id=%s).", message.webhook_id)
            return

        # 4. Connection guard – silently drop if bot is not in a voice channel.
        if not self._voice_manager.is_connected:
            logger.debug(
                "ListenerCog: bot not in voice channel; dropping message from %s.",
                message.author,
            )
            return

        # 5. Sanitise the text.
        text = sanitise_for_tts(message.content)
        if text is None:
            logger.debug(
                "ListenerCog: message from %s produced empty TTS text after sanitisation.",
                message.author,
            )
            return

        # 6. Enqueue.
        enqueued = await self._voice_manager.enqueue(text)
        if enqueued:
            logger.info(
                "ListenerCog: enqueued message from %s: %r",
                message.author,
                text[:60],
            )
        else:
            logger.warning(
                "ListenerCog: could not enqueue message from %s (queue full?).",
                message.author,
            )


async def setup(bot: commands.Bot) -> None:
    """Entry point called by :meth:`discord.ext.commands.Bot.load_extension`."""
    await bot.add_cog(ListenerCog(bot))
    logger.info("ListenerCog loaded.")
