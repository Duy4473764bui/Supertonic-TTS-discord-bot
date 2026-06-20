"""
cogs/join.py - Slash command cog that lets users invite the bot to a voice channel.

Commands
--------
/join   – Bot joins the voice channel the user is currently in.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from core.voice import VoiceManager

logger = logging.getLogger(__name__)


class JoinCog(commands.Cog, name="Join"):
    """Cog that provides the ``/join`` slash command."""

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
    # Slash commands
    # ------------------------------------------------------------------

    @app_commands.command(
        name="join",
        description="Invite the TTS bot to your current voice channel.",
    )
    async def join(self, interaction: discord.Interaction) -> None:
        """Handle the ``/join`` slash command.

        Rules:
        - The invoking user **must** be in a voice channel.
        - If the bot is already connected somewhere, refuse politely.
        - Otherwise, connect and confirm.
        """
        # 1. Check that the user is in a voice channel.
        if (
            not isinstance(interaction.user, discord.Member)
            or interaction.user.voice is None
            or interaction.user.voice.channel is None
        ):
            await interaction.response.send_message(
                "❌ You must be connected to a voice channel first!",
                ephemeral=True,
            )
            return

        target_channel: discord.VoiceChannel = interaction.user.voice.channel  # type: ignore[assignment]

        # 2. Refuse if the bot is already in another channel.
        if self._voice_manager.is_connected:
            current = self._voice_manager.voice_channel
            if current and current.id != target_channel.id:
                await interaction.response.send_message(
                    f"⚠️ I'm already reading in **{current.name}**! "
                    "Ask me to leave there first if you'd like me to move.",
                    ephemeral=True,
                )
                return

            # Bot is already in the *same* channel – no-op.
            if current and current.id == target_channel.id:
                await interaction.response.send_message(
                    f"✅ I'm already in **{current.name}** and listening!",
                    ephemeral=True,
                )
                return

        # 3. Defer so we have time to connect (network round-trip).
        await interaction.response.defer(ephemeral=False, thinking=True)

        success = await self._voice_manager.connect(target_channel)

        if success:
            await interaction.followup.send(
                f"🔊 Joined **{target_channel.name}** and will now read "
                f"messages from <#{self.bot.text_channel_id}> aloud!"  # type: ignore[attr-defined]
            )
            logger.info(
                "JoinCog: connected to '%s' on behalf of %s.",
                target_channel.name,
                interaction.user,
            )
        else:
            await interaction.followup.send(
                "❌ I couldn't join the voice channel. Please check my permissions "
                "and try again.",
            )
            logger.error(
                "JoinCog: failed to connect to '%s'.", target_channel.name
            )


async def setup(bot: commands.Bot) -> None:
    """Entry point called by :meth:`discord.ext.commands.Bot.load_extension`."""
    await bot.add_cog(JoinCog(bot))
    logger.info("JoinCog loaded.")
