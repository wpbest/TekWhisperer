from __future__ import annotations

from collections.abc import Callable

SPECIAL_KEYS = {
    "ctrl": "<ctrl>",
    "control": "<ctrl>",
    "alt": "<alt>",
    "shift": "<shift>",
    "cmd": "<cmd>",
    "win": "<cmd>",
    "space": "<space>",
    "enter": "<enter>",
    "return": "<enter>",
    "esc": "<esc>",
    "escape": "<esc>",
}


def start_global_hotkey(hotkey: str, callback: Callable[[], None]):
    from pynput import keyboard

    listener = keyboard.GlobalHotKeys({normalize_hotkey(hotkey): callback})
    listener.start()
    return listener


def normalize_hotkey(hotkey: str) -> str:
    parts = [part.strip() for part in hotkey.split("+") if part.strip()]
    normalized: list[str] = []
    for part in parts:
        lowered = part.lower()
        if part.startswith("<") and part.endswith(">"):
            normalized.append(part)
        else:
            normalized.append(SPECIAL_KEYS.get(lowered, lowered))
    return "+".join(normalized)
