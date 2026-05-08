from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from .audio import AudioRecorder
from .brain import OpenAICodeBridge
from .config import AppConfig
from .hotkeys import start_global_hotkey
from .injector import CodeInjector
from .stt import FasterWhisperTranscriber
from .tts import SpeechEngine

LOGGER = logging.getLogger(__name__)


@dataclass
class RuntimeState:
    paused: bool = False
    recording: bool = False
    status: str = "Ready"


class TekWhispererApp:
    def __init__(self, config: AppConfig):
        self.config = config
        self.state = RuntimeState()
        self._lock = threading.RLock()
        self._stop_recording = threading.Event()
        self._worker: threading.Thread | None = None
        self._hotkey_listener = None
        self._icon = None

        self.recorder = AudioRecorder(config.recording)
        self.transcriber = FasterWhisperTranscriber(config.whisper)
        self.bridge = OpenAICodeBridge(config.openai)
        self.injector = CodeInjector(config.injection)
        self.speech = SpeechEngine(config.tts)

    def run(self) -> None:
        from pystray import Icon, Menu, MenuItem

        self.config.data_dir.mkdir(parents=True, exist_ok=True)
        self._hotkey_listener = start_global_hotkey(
            self.config.hotkeys.toggle_recording,
            self.toggle_recording,
        )

        self._icon = Icon(
            "Tek Whisperer",
            _create_icon_image(),
            title="Tek Whisperer",
            menu=Menu(
                MenuItem("Toggle recording", self._menu_toggle_recording, default=True),
                MenuItem("Pause hotkey", self._menu_toggle_pause, checked=lambda _item: self.state.paused),
                MenuItem("Open config folder", self._menu_open_config_folder),
                MenuItem("Quit", self._menu_quit),
            ),
        )
        self._notify("Tek Whisperer ready", f"Hotkey: {self.config.hotkeys.toggle_recording}")
        LOGGER.info("Tek Whisperer tray app started")
        self._icon.run()

    def toggle_recording(self) -> None:
        with self._lock:
            if self.state.paused:
                self._notify("Tek Whisperer paused", "Resume from the tray menu to listen again.")
                return
            if self.state.recording:
                self._stop_recording.set()
                self._set_status("Stopping")
                return

            self._stop_recording.clear()
            self.state.recording = True
            self._set_status("Listening")
            self._worker = threading.Thread(target=self._record_and_process, daemon=True)
            self._worker.start()

    def _record_and_process(self) -> None:
        try:
            self._notify("Listening", "Press the hotkey again to stop and process.")
            audio = self.recorder.record_until_stopped(self._stop_recording)
            if audio.duration_seconds < self.config.recording.min_seconds:
                self._notify("Too short", "Recording ignored.")
                return

            self._set_status("Transcribing")
            transcript = self.transcriber.transcribe(audio)
            if not transcript:
                self._notify("No speech detected", "Try again a little closer to the microphone.")
                self.speech.speak("I did not catch that.")
                return

            self._set_status("Thinking")
            response = self.bridge.generate(transcript)

            self._set_status("Injecting")
            injection = self.injector.inject(response.code)
            LOGGER.info("Injection result: %s - %s", injection.status, injection.detail)

            self._set_status("Speaking")
            self.speech.speak(response.spoken or injection.detail)
            self._notify("Tek Whisperer", injection.detail)
        except Exception as exc:
            LOGGER.exception("Tek Whisperer workflow failed")
            self._notify("Tek Whisperer error", str(exc))
            try:
                self.speech.speak("Tek Whisperer hit an error. Check the log for details.")
            except Exception:
                LOGGER.debug("Could not speak error message", exc_info=True)
        finally:
            with self._lock:
                self.state.recording = False
                self._stop_recording.clear()
                self._set_status("Ready")

    def _menu_toggle_recording(self, _icon, _item) -> None:
        self.toggle_recording()

    def _menu_toggle_pause(self, _icon, _item) -> None:
        with self._lock:
            self.state.paused = not self.state.paused
            if self.state.paused and self.state.recording:
                self._stop_recording.set()
            self._set_status("Paused" if self.state.paused else "Ready")

    def _menu_open_config_folder(self, _icon, _item) -> None:
        open_folder(self.config.data_dir)

    def _menu_quit(self, icon, _item) -> None:
        self._stop_recording.set()
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        icon.stop()

    def _set_status(self, status: str) -> None:
        self.state.status = status
        if self._icon:
            self._icon.title = f"Tek Whisperer - {status}"
            try:
                self._icon.update_menu()
            except Exception:
                LOGGER.debug("Tray menu update failed", exc_info=True)

    def _notify(self, title: str, message: str) -> None:
        LOGGER.info("%s: %s", title, message)
        if self._icon:
            try:
                self._icon.notify(message, title)
            except Exception:
                LOGGER.debug("Tray notification failed", exc_info=True)


def open_folder(path: Path) -> None:
    import os
    import platform
    import subprocess

    path.mkdir(parents=True, exist_ok=True)
    system = platform.system()
    if system == "Windows":
        os.startfile(path)  # noqa: S606 - user-triggered tray action
    elif system == "Darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _create_icon_image():
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((8, 8, 56, 56), radius=12, fill=(16, 18, 24, 255))
    draw.ellipse((20, 12, 44, 36), fill=(64, 180, 160, 255))
    draw.rounded_rectangle((28, 31, 36, 46), radius=4, fill=(64, 180, 160, 255))
    draw.line((20, 48, 44, 48), fill=(230, 235, 240, 255), width=4)
    draw.line((32, 46, 32, 54), fill=(230, 235, 240, 255), width=4)
    return image
