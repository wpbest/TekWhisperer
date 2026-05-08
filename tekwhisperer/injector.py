from __future__ import annotations

import logging
import platform
import time
from dataclasses import dataclass

from .config import InjectionConfig

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class InjectionResult:
    status: str
    detail: str
    active_window_title: str | None = None


class CodeInjector:
    def __init__(self, config: InjectionConfig):
        self.config = config

    def inject(self, text: str) -> InjectionResult:
        if not text.strip():
            return InjectionResult(status="skipped", detail="No code returned.")

        mode = self.config.mode.lower()
        if mode == "off":
            return InjectionResult(status="skipped", detail="Injection is disabled.")

        active_title = active_window_title()
        if mode in {"paste", "typewrite"} and not self._window_allowed(active_title):
            self._copy_to_clipboard(text)
            return InjectionResult(
                status="clipboard",
                detail="Active window was not allowlisted, so code was copied only.",
                active_window_title=active_title,
            )

        if mode == "clipboard":
            self._copy_to_clipboard(text)
            return InjectionResult(
                status="clipboard",
                detail="Code copied to clipboard.",
                active_window_title=active_title,
            )

        if mode == "paste":
            self._paste(text)
            return InjectionResult(
                status="pasted",
                detail="Code pasted into the active IDE window.",
                active_window_title=active_title,
            )

        if mode == "typewrite":
            self._typewrite(text)
            return InjectionResult(
                status="typed",
                detail="Code typed into the active IDE window.",
                active_window_title=active_title,
            )

        raise ValueError(f"Unsupported injection mode: {self.config.mode}")

    def _window_allowed(self, active_title: str | None) -> bool:
        if not self.config.require_allowed_window:
            return True
        if not active_title:
            return False

        title = active_title.lower()
        return any(keyword.lower() in title for keyword in self.config.allowed_window_keywords)

    def _copy_to_clipboard(self, text: str) -> None:
        import pyperclip

        pyperclip.copy(text)

    def _paste(self, text: str) -> None:
        import pyautogui
        import pyperclip

        previous_clipboard = None
        if self.config.restore_clipboard_after_paste:
            try:
                previous_clipboard = pyperclip.paste()
            except Exception:
                LOGGER.debug("Could not read clipboard before paste", exc_info=True)

        pyperclip.copy(text)
        time.sleep(self.config.paste_delay_seconds)
        keys = [part.strip().lower() for part in self.config.paste_hotkey.split("+") if part.strip()]
        pyautogui.hotkey(*keys)

        if self.config.restore_clipboard_after_paste and previous_clipboard is not None:
            time.sleep(max(0.25, self.config.paste_delay_seconds))
            pyperclip.copy(previous_clipboard)

    def _typewrite(self, text: str) -> None:
        import pyautogui

        pyautogui.write(text, interval=self.config.typewrite_interval_seconds)


def active_window_title() -> str | None:
    if platform.system() != "Windows":
        return None

    try:
        import pygetwindow as gw

        window = gw.getActiveWindow()
        return window.title if window else None
    except Exception:
        LOGGER.debug("Could not read active window title", exc_info=True)
        return None
