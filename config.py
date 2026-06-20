"""
config.py - Central configuration for the Discord TTS Bot.

Edit the values below before running the bot.
All sensitive values (TOKEN) should ideally be loaded from environment variables
in production; a .env approach is shown in the comments.
"""

import os

# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

# Bot token from https://discord.com/developers/applications
# Prefer: TOKEN = os.getenv("DISCORD_TOKEN", "")
TOKEN: str = os.getenv("DISCORD_TOKEN", "YOUR_BOT_TOKEN_HERE")

# The ID of the text channel the bot will listen to and read aloud.
# Right-click the channel in Discord → "Copy Channel ID" (Developer Mode must be on).
TEXT_CHANNEL_ID: int = int(os.getenv("TEXT_CHANNEL_ID", "0"))

# ---------------------------------------------------------------------------
# TTS / Supertonic
# ---------------------------------------------------------------------------

# BCP-47 language/locale tag passed to Supertonic.
# Vietnamese:  "vi"
# English US:  "en-US"
VOICE_LANGUAGE: str = os.getenv("VOICE_LANGUAGE", "vi")

# Optional: Supertonic speaker / voice ID (leave empty for default).
VOICE_SPEAKER: str = os.getenv("VOICE_SPEAKER", "")

# Sample rate for generated WAV files (Hz).
AUDIO_SAMPLE_RATE: int = 22050

# ---------------------------------------------------------------------------
# FFmpeg
# ---------------------------------------------------------------------------

# Absolute path to the ffmpeg executable.
# Windows example : r"C:\ffmpeg\bin\ffmpeg.exe"
# Linux / macOS   : "/usr/bin/ffmpeg"   or just "ffmpeg" if it is on PATH
FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")

# FFmpeg options forwarded to discord.py's FFmpegPCMAudio.
# Adjust before_options / options if you experience audio glitches.
FFMPEG_BEFORE_OPTIONS: str = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
FFMPEG_OPTIONS: str = "-vn"

# ---------------------------------------------------------------------------
# Bot behaviour
# ---------------------------------------------------------------------------

# Maximum number of messages waiting in the TTS queue.
# Messages that arrive while the queue is full are silently dropped.
QUEUE_MAX_SIZE: int = 50

# How often (seconds) the bot checks whether the voice channel is empty.
EMPTY_CHANNEL_CHECK_INTERVAL: float = 5.0

# Directory where temporary WAV files are stored (auto-created on startup).
AUDIO_TMP_DIR: str = os.path.join(os.path.dirname(__file__), "audio")
