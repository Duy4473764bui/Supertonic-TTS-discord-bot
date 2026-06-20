"""
main.py - Discord TTS Bot entry point.

Responsibilities
----------------
* Create and configure the :class:`discord.ext.commands.Bot` instance.
* Attach the shared :class:`~core.voice.VoiceManager`.
* Load all cogs.
* Sync slash commands on startup.
* Run the bot.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import discord
from discord.ext import commands

import config
from core.utils import setup_logging
from core.voice import VoiceManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Intents
# ---------------------------------------------------------------------------

_INTENTS = discord.Intents.default()
_INTENTS.message_content = True   # Required to read message text (Privileged intent)
_INTENTS.voice_states = True       # Required to detect voice channel membership
_INTENTS.members = True            # Required to check human/bot status in channels

# ---------------------------------------------------------------------------
# Cog extensions to load (relative module paths)
# ---------------------------------------------------------------------------

EXTENSIONS: tuple[str, ...] = (
    "cogs.join",
    "cogs.listener",
)


# ---------------------------------------------------------------------------
# Bot subclass
# ---------------------------------------------------------------------------

class TTSBot(commands.Bot):
    """Custom :class:`~discord.ext.commands.Bot` subclass.

    Adds:
    - ``voice_manager``: shared :class:`~core.voice.VoiceManager` instance.
    - ``text_channel_id``: integer ID of the monitored text channel.
    - Automatic slash-command sync on ``on_ready``.
    """

    def __init__(self) -> None:
        super().__init__(
            command_prefix=commands.when_mentioned,  # Prefix commands disabled; slash only.
            intents=_INTENTS,
            help_command=None,
        )
        # Shared state, accessible from all cogs via self.bot.voice_manager
        self.voice_manager: VoiceManager = VoiceManager(self)
        self.text_channel_id: int = config.TEXT_CHANNEL_ID

    # ------------------------------------------------------------------
    # Setup hook (called before login)
    # ------------------------------------------------------------------

    async def setup_hook(self) -> None:
        """Load cog extensions before the bot connects."""
        logger.info("TTSBot: loading extensions …")
        for ext in EXTENSIONS:
            try:
                await self.load_extension(ext)
                logger.info("TTSBot: loaded extension '%s'.", ext)
            except Exception:
                logger.exception("TTSBot: failed to load extension '%s'.", ext)
                sys.exit(1)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    async def on_ready(self) -> None:
        """Sync slash commands and log startup info."""
        assert self.user is not None  # appease type checkers
        logger.info("TTSBot: logged in as %s (id=%d).", self.user, self.user.id)

        # Sync slash commands globally (may take up to 1 hour to propagate).
        # For instant updates during development, pass `guild=discord.Object(id=YOUR_GUILD_ID)`.
        try:
            synced = await self.tree.sync()
            logger.info("TTSBot: synced %d slash command(s).", len(synced))
        except discord.HTTPException:
            logger.exception("TTSBot: failed to sync slash commands.")

        # Validate that the configured text channel exists and is accessible.
        channel = self.get_channel(config.TEXT_CHANNEL_ID)
        if channel is None:
            logger.error(
                "TTSBot: TEXT_CHANNEL_ID=%d not found or bot has no access.  "
                "Check config.py.",
                config.TEXT_CHANNEL_ID,
            )
        else:
            logger.info(
                "TTSBot: monitoring text channel '#%s' (id=%d).",
                getattr(channel, "name", "?"),
                channel.id,
            )

        logger.info("TTSBot: ready and waiting for /join commands.")

    async def on_error(self, event: str, *args, **kwargs) -> None:  # type: ignore[override]
        logger.exception("TTSBot: unhandled error in event '%s'.", event)

    async def close(self) -> None:
        """Clean up before shutdown."""
        logger.info("TTSBot: shutting down …")
        if self.voice_manager.is_connected:
            await self.voice_manager.disconnect()
        await super().close()
        logger.info("TTSBot: goodbye.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    setup_logging(logging.INFO)

    # Validate essential configuration before connecting.
    if not config.TOKEN or config.TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.critical(
            "TOKEN is not set in config.py.  "
            "Set the DISCORD_TOKEN environment variable or edit config.py."
        )
        sys.exit(1)

    if config.TEXT_CHANNEL_ID == 0:
        logger.critical(
            "TEXT_CHANNEL_ID is not set in config.py.  "
            "Set the TEXT_CHANNEL_ID environment variable or edit config.py."
        )
        sys.exit(1)

    # Ensure the audio temp directory exists.
    Path(config.AUDIO_TMP_DIR).mkdir(parents=True, exist_ok=True)

    bot = TTSBot()
    async with bot:
        await bot.start(config.TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
