"""
core/tts.py - Supertonic TTS engine wrapper.

Wraps the `supertonic` Python package to generate temporary WAV files
from arbitrary text strings.  The caller is responsible for deleting the
file after playback (see VoiceManager which does this automatically).
"""

from __future__ import annotations

import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class TTSEngine:
    """Thin, reusable wrapper around the Supertonic TTS library.

    Usage::

        engine = TTSEngine()
        wav_path = await engine.synthesize("Xin chào mọi người!")
        # … play wav_path …
        os.remove(wav_path)   # or let VoiceManager clean up
    """

    def __init__(
        self,
        language: str = config.VOICE_LANGUAGE,
        speaker: str = config.VOICE_SPEAKER,
        sample_rate: int = config.AUDIO_SAMPLE_RATE,
        output_dir: str = config.AUDIO_TMP_DIR,
    ) -> None:
        self._language = language
        self._speaker = speaker
        self._sample_rate = sample_rate
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Lazy-import so the rest of the bot still loads even if the package
        # is not yet installed (helpful during development / CI).
        self._tts = self._load_supertonic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def synthesize(self, text: str) -> Optional[str]:
        """Convert *text* to speech and write a WAV file.

        Returns the absolute path to the generated WAV file, or ``None``
        if synthesis fails.

        This method runs the (potentially blocking) Supertonic call in the
        default executor so it does not block the asyncio event loop.
        """
        if not text.strip():
            logger.debug("TTSEngine.synthesize called with empty text – skipped.")
            return None

        if self._tts is None:
            logger.error("Supertonic is not available; cannot synthesize TTS.")
            return None

        import asyncio

        loop = asyncio.get_running_loop()
        try:
            wav_path = await loop.run_in_executor(None, self._synthesize_blocking, text)
            return wav_path
        except Exception:
            logger.exception("TTSEngine: synthesis failed for text: %r", text[:80])
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _synthesize_blocking(self, text: str) -> str:
        """Blocking synthesis call (runs in a thread-pool executor).

        Returns the path to the written WAV file.
        """
        filename = f"tts_{uuid.uuid4().hex}.wav"
        output_path = str(self._output_dir / filename)

        logger.debug("TTSEngine: synthesizing %d chars → %s", len(text), output_path)

        # ------------------------------------------------------------------
        # Supertonic API call
        # The public Supertonic API (pip install supertonic) exposes:
        #
        #   from supertonic import TTS
        #   tts = TTS(language="vi")
        #   tts.tts_to_file(text=text, file_path=output_path)
        #
        # If your installed version differs, adjust the call below.
        # ------------------------------------------------------------------
        if self._speaker:
            self._tts.tts_to_file(
                text=text,
                speaker=self._speaker,
                file_path=output_path,
            )
        else:
            self._tts.tts_to_file(
                text=text,
                file_path=output_path,
            )

        logger.info("TTSEngine: wrote WAV → %s", output_path)
        return output_path

    @staticmethod
    def _load_supertonic():
        """Import and initialise the Supertonic TTS object.

        Returns the TTS instance, or ``None`` if the package is missing.
        """
        try:
            from supertonic import TTS  # type: ignore[import]

            language = config.VOICE_LANGUAGE
            logger.info("TTSEngine: loading Supertonic model for language=%r …", language)
            instance = TTS(language=language)
            logger.info("TTSEngine: Supertonic model loaded successfully.")
            return instance
        except ImportError:
            logger.critical(
                "The 'supertonic' package is not installed.  "
                "Run:  pip install supertonic"
            )
            return None
        except Exception:
            logger.exception("TTSEngine: failed to initialise Supertonic.")
            return None
