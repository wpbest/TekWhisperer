from __future__ import annotations

import logging

from .audio import RecordedAudio
from .config import WhisperConfig

LOGGER = logging.getLogger(__name__)


class FasterWhisperTranscriber:
    def __init__(self, config: WhisperConfig):
        self.config = config
        self._model = None

    def transcribe(self, audio: RecordedAudio) -> str:
        if audio.duration_seconds <= 0 or getattr(audio.samples, "size", 0) == 0:
            return ""

        model = self._load_model()
        segments, info = model.transcribe(
            audio.samples,
            language=self.config.language or None,
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad_filter,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        LOGGER.info("Transcribed %.2fs audio as %r", audio.duration_seconds, text)
        LOGGER.debug("Whisper language=%s probability=%s", info.language, info.language_probability)
        return text

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel

            LOGGER.info(
                "Loading Faster-Whisper model=%s device=%s compute_type=%s",
                self.config.model,
                self.config.device,
                self.config.compute_type,
            )
            self._model = WhisperModel(
                self.config.model,
                device=self.config.device,
                compute_type=self.config.compute_type,
            )
        return self._model
