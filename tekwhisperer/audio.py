from __future__ import annotations

import io
import time
import wave
from dataclasses import dataclass
from threading import Event

from .config import RecordingConfig


@dataclass(frozen=True)
class RecordedAudio:
    samples: object
    sample_rate: int
    duration_seconds: float


class AudioRecorder:
    def __init__(self, config: RecordingConfig):
        self.config = config

    def record_until_stopped(self, stop_event: Event) -> RecordedAudio:
        import numpy as np
        import sounddevice as sd

        frames: list[object] = []
        started_at = time.monotonic()
        blocksize = max(1, int(self.config.sample_rate * self.config.block_seconds))
        device = self.config.device if self.config.device not in ("", None) else None

        def callback(indata: object, _frames: int, _time_info: object, status: object) -> None:
            if status:
                # sounddevice status values are diagnostic, not fatal. The tray logger records them.
                pass
            frames.append(indata.copy())

        with sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype="float32",
            blocksize=blocksize,
            device=device,
            callback=callback,
        ):
            while not stop_event.wait(0.05):
                if time.monotonic() - started_at >= self.config.max_seconds:
                    break

        duration = time.monotonic() - started_at
        if not frames:
            return RecordedAudio(
                samples=np.array([], dtype="float32"),
                sample_rate=self.config.sample_rate,
                duration_seconds=duration,
            )

        audio = np.concatenate(frames, axis=0).astype("float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        else:
            audio = audio.reshape(-1)
        return RecordedAudio(samples=audio, sample_rate=self.config.sample_rate, duration_seconds=duration)


def play_wav_bytes(audio_bytes: bytes) -> None:
    import numpy as np
    import sounddevice as sd

    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        frame_bytes = wav_file.readframes(wav_file.getnframes())

    if sample_width == 1:
        audio = np.frombuffer(frame_bytes, dtype=np.uint8).astype("float32")
        audio = (audio - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(frame_bytes, dtype=np.int16).astype("float32") / 32768.0
    elif sample_width == 4:
        audio = np.frombuffer(frame_bytes, dtype=np.int32).astype("float32") / 2147483648.0
    else:
        raise ValueError(f"Unsupported WAV sample width: {sample_width}")

    if channels > 1:
        audio = audio.reshape(-1, channels)

    sd.play(audio, sample_rate)
    sd.wait()
