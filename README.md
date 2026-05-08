# Tek Whisperer

Tek Whisperer is an unobtrusive Python tray utility that bridges speech and code. It records a voice command from a global hotkey, transcribes it locally with Faster-Whisper, asks Anthropic Claude (Sonnet 4.6 by default) for a paste-ready coding response, speaks the explanation with AI-generated TTS, and injects the generated code into Codex, VS Code, Cursor, or another allowlisted IDE window.

It is designed to be visible and consent-based: the tray icon shows when it is running, the hotkey explicitly starts and stops listening, and paste injection is guarded by an active-window allowlist.

## What It Does

- Lives in the system tray with pause, record, config-folder, and quit controls.
- Uses Faster-Whisper for local microphone transcription.
- Uses Anthropic Claude (Sonnet 4.6 by default) for coding responses through the Messages API, with structured-output enforcement so replies are always valid JSON.
- Uses OpenAI `gpt-4o-mini-tts` by default for spoken explanations, with a system voice fallback.
- Copies or pastes generated code into the active IDE window.
- Refuses to paste into non-allowlisted windows by default and copies to the clipboard instead.

## Quick Start

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Set both API keys (Anthropic for the coding brain, OpenAI for TTS):

```powershell
setx ANTHROPIC_API_KEY "sk-ant-..."
setx OPENAI_API_KEY    "sk-..."
```

Close and reopen PowerShell so the variables are visible to subsequent shells. If you'd rather not pay for OpenAI TTS, set `[tts] enabled = false` in your config and Tek Whisperer falls back to the system voice via `pyttsx3`.

Create a user config:

```powershell
tek-whisperer --init-config
```

Start the tray app:

```powershell
tek-whisperer
```

Default hotkey: `Ctrl+Alt+Space`

1. Focus your Codex IDE, VS Code, or Cursor editor.
2. Press `Ctrl+Alt+Space` to start listening.
3. Speak a coding request.
4. Press `Ctrl+Alt+Space` again to stop.
5. Tek Whisperer transcribes, generates, speaks, and pastes when the active window is allowlisted.

## Configuration

The default config path is:

- Windows: `%USERPROFILE%\.tekwhisperer\config.toml`
- macOS/Linux: `~/.tekwhisperer/config.toml`

You can also pass a config path:

```powershell
tek-whisperer --config .\config.example.toml
```

Important settings:

```toml
[anthropic]
model = "claude-sonnet-4-6"
thinking_enabled = false   # flip on for hard problems; adds 1-3s latency
effort = "medium"          # only used when thinking_enabled = true

[tts]
provider = "openai"
model = "gpt-4o-mini-tts"
voice = "marin"

[injection]
mode = "paste"
require_allowed_window = true
allowed_window_keywords = ["Codex", "Visual Studio Code", "VS Code", "Cursor"]
```

Injection modes:

- `off`: never inject.
- `clipboard`: copy generated code only.
- `paste`: copy generated code and press `Ctrl+V` when the focused window is allowlisted.
- `typewrite`: type generated code into the focused allowlisted window.

## One-Shot Test

You can test the OpenAI response path without the tray:

```powershell
tek-whisperer --command "Write a Python function that slugifies a title"
```

Add `--inject` to use the configured injection mode, or `--speak` to hear the explanation.

## Notes

- Faster-Whisper models download on first use.
- `sounddevice` needs access to your microphone and speakers.
- The OpenAI voice is AI-generated; disclose that clearly if other people hear it.
- The tray app does not hide itself, evade monitoring, or paste outside the configured allowlist by default.

## Sources

- Anthropic Messages API reference: https://platform.claude.com/docs/en/api/messages
- Anthropic structured outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Anthropic model selection: https://platform.claude.com/docs/en/about-claude/models/overview
- OpenAI text-to-speech docs: https://developers.openai.com/api/docs/guides/text-to-speech
