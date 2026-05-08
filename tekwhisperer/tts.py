from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from .audio import play_wav_bytes
from .config import TTSConfig

LOGGER = logging.getLogger(__name__)


class SpeechEngine:
    def __init__(self, config: TTSConfig):
        self.config = config
        self._openai_client = None

    def speak(self, text: str) -> None:
        if not self.config.enabled or not text.strip():
            return

        if self.config.provider.lower() == "openai":
            try:
                audio = self._openai_tts(text)
                play_wav_bytes(audio)
                return
            except Exception:
                LOGGER.exception("OpenAI TTS failed")
                if not self.config.fallback_system_voice:
                    raise

        self._system_voice(text)

    def _openai_tts(self, text: str) -> bytes:
        client = self._load_openai_client()
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            speech_path = Path(temp_file.name)

        try:
            with client.audio.speech.with_streaming_response.create(
                model=self.config.model,
                voice=self.config.voice,
                input=text[:4096],
                instructions=self.config.instructions,
                response_format="wav",
            ) as response:
                response.stream_to_file(speech_path)
            return speech_path.read_bytes()
        finally:
            speech_path.unlink(missing_ok=True)

    def _load_openai_client(self):
        if self._openai_client is None:
            from openai import OpenAI

            self._openai_client = OpenAI()
        return self._openai_client

    @staticmethod
    def _system_voice(text: str) -> None:
        import pyttsx3

        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
