"""
core/utils.py - Shared utility helpers used across the bot.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

# Regex to strip Discord formatting marks that look noisy when read aloud.
_DISCORD_MENTION_RE = re.compile(r"<[@#!&][^>]+>")
_URL_RE = re.compile(r"https?://\S+")
_CUSTOM_EMOJI_RE = re.compile(r"<a?:[A-Za-z0-9_]+:\d+>")
_MARKDOWN_RE = re.compile(r"(\*{1,3}|_{1,3}|~~|`{1,3})")


def sanitise_for_tts(text: str, max_length: int = 500) -> Optional[str]:
    """Clean *text* so it is suitable for TTS synthesis.

    Steps applied (in order):

    1. Strip Discord mentions (``@user``, ``#channel``, ``@role``).
    2. Strip custom emoji (``<:name:id>``).
    3. Replace URLs with the word "link".
    4. Remove Markdown formatting characters.
    5. Normalise Unicode (NFC).
    6. Collapse whitespace.
    7. Truncate to *max_length* characters.

    Returns ``None`` if the resulting string is empty.
    """
    # 1. Mentions
    text = _DISCORD_MENTION_RE.sub("", text)
    # 2. Custom emoji
    text = _CUSTOM_EMOJI_RE.sub("", text)
    # 3. URLs
    text = _URL_RE.sub("link", text)
    # 4. Markdown
    text = _MARKDOWN_RE.sub("", text)
    # 5. Unicode normalise
    text = unicodedata.normalize("NFC", text)
    # 6. Whitespace
    text = " ".join(text.split())
    # 7. Truncate
    if len(text) > max_length:
        text = text[:max_length].rstrip()
        logger.debug("sanitise_for_tts: text truncated to %d chars.", max_length)

    return text if text else None


def setup_logging(level: int = logging.INFO) -> None:
    """Configure root logger with a sensible format."""
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Silence overly chatty third-party loggers.
    for noisy in ("discord.gateway", "discord.client", "discord.http"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
