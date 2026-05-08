from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

DEFAULT_SYSTEM_PROMPT = """You are Tek Whisperer, a concise hands-free coding copilot.

The user speaks coding commands that should become useful IDE text. Return a JSON object with:
- "spoken": one to three short sentences explaining what you produced or what the user should know.
- "code": raw code or editor text to inject. Use an empty string when no insertion is useful.

Rules:
- Do not wrap code in Markdown fences unless the user explicitly asks for Markdown.
- Prefer complete, paste-ready snippets over vague advice.
- If the user asks a question rather than requesting code, put the answer in "spoken" and leave "code" empty.
- If a request is ambiguous, make a conservative assumption and mention it in "spoken".
"""


def default_data_dir() -> Path:
    return Path.home() / ".tekwhisperer"


def default_config_path() -> Path:
    env_path = os.environ.get("TEKWHISPERER_CONFIG")
    return Path(env_path).expanduser() if env_path else default_data_dir() / "config.toml"


@dataclass
class RecordingConfig:
    sample_rate: int = 16000
    channels: int = 1
    max_seconds: float = 30.0
    min_seconds: float = 0.35
    block_seconds: float = 0.10
    device: str | int | None = None


@dataclass
class WhisperConfig:
    model: str = "small.en"
    device: str = "auto"
    compute_type: str = "auto"
    language: str | None = "en"
    beam_size: int = 5
    vad_filter: bool = True


@dataclass
class OpenAIConfig:
    model: str = "gpt-5.5"
    reasoning_effort: str = "medium"
    max_output_tokens: int = 4096
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


@dataclass
class TTSConfig:
    enabled: bool = True
    provider: str = "openai"
    model: str = "gpt-4o-mini-tts"
    voice: str = "marin"
    instructions: str = (
        "Speak clearly and calmly, like a senior pair programmer giving concise guidance."
    )
    fallback_system_voice: bool = True


@dataclass
class InjectionConfig:
    mode: str = "paste"
    require_allowed_window: bool = True
    allowed_window_keywords: list[str] = field(
        default_factory=lambda: ["Codex", "Visual Studio Code", "VS Code", "Cursor"]
    )
    paste_hotkey: str = "ctrl+v"
    paste_delay_seconds: float = 0.10
    restore_clipboard_after_paste: bool = False
    typewrite_interval_seconds: float = 0.0


@dataclass
class HotkeysConfig:
    toggle_recording: str = "<ctrl>+<alt>+<space>"


@dataclass
class AppConfig:
    data_dir: Path = field(default_factory=default_data_dir)
    log_level: str = "INFO"
    recording: RecordingConfig = field(default_factory=RecordingConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    tts: TTSConfig = field(default_factory=TTSConfig)
    injection: InjectionConfig = field(default_factory=InjectionConfig)
    hotkeys: HotkeysConfig = field(default_factory=HotkeysConfig)
    config_path: Path | None = None


def load_config(path: str | os.PathLike[str] | None = None) -> AppConfig:
    config_path = Path(path).expanduser() if path else default_config_path()
    config = AppConfig(config_path=config_path)

    if not config_path.exists():
        return config

    data = tomllib.loads(config_path.read_text(encoding="utf-8"))
    app_data = data.get("app", {})
    _apply_values(config, app_data)

    for section_name in ("recording", "whisper", "openai", "tts", "injection", "hotkeys"):
        section_data = data.get(section_name, {})
        if section_data:
            _apply_values(getattr(config, section_name), section_data)

    return config


def write_default_config(
    path: str | os.PathLike[str] | None = None,
    *,
    overwrite: bool = False,
) -> Path:
    config_path = Path(path).expanduser() if path else default_config_path()
    if config_path.exists() and not overwrite:
        raise FileExistsError(f"Config already exists: {config_path}")

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(default_config_toml(), encoding="utf-8")
    return config_path


def default_config_toml() -> str:
    prompt = DEFAULT_SYSTEM_PROMPT.replace('"""', '\\"\\"\\"').strip()
    return f'''# Tek Whisperer configuration

[app]
data_dir = "{_toml_escape(str(default_data_dir()))}"
log_level = "INFO"

[hotkeys]
toggle_recording = "<ctrl>+<alt>+<space>"

[recording]
sample_rate = 16000
channels = 1
max_seconds = 30.0
min_seconds = 0.35
block_seconds = 0.10
device = ""

[whisper]
model = "small.en"
device = "auto"
compute_type = "auto"
language = "en"
beam_size = 5
vad_filter = true

[openai]
model = "gpt-5.5"
reasoning_effort = "medium"
max_output_tokens = 4096
system_prompt = """{prompt}"""

[tts]
enabled = true
provider = "openai"
model = "gpt-4o-mini-tts"
voice = "marin"
instructions = "Speak clearly and calmly, like a senior pair programmer giving concise guidance."
fallback_system_voice = true

[injection]
mode = "paste"
require_allowed_window = true
allowed_window_keywords = ["Codex", "Visual Studio Code", "VS Code", "Cursor"]
paste_hotkey = "ctrl+v"
paste_delay_seconds = 0.10
restore_clipboard_after_paste = false
typewrite_interval_seconds = 0.0
'''


def _apply_values(target: Any, values: dict[str, Any]) -> None:
    valid_fields = {item.name: item for item in fields(target)}
    for key, value in values.items():
        field_info = valid_fields.get(key)
        if field_info is None or key == "config_path":
            continue

        current_value = getattr(target, key)
        if is_dataclass(current_value):
            continue

        setattr(target, key, _coerce_value(value, current_value))


def _coerce_value(value: Any, current_value: Any) -> Any:
    if isinstance(current_value, Path):
        return Path(str(value)).expanduser()
    if current_value is None and value == "":
        return None
    if isinstance(current_value, bool):
        return bool(value)
    if isinstance(current_value, int) and not isinstance(current_value, bool):
        return int(value)
    if isinstance(current_value, float):
        return float(value)
    return value


def _toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')
