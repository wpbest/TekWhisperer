from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from .config import AnthropicConfig

LOGGER = logging.getLogger(__name__)


_REPLY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "spoken": {
            "type": "string",
            "description": "One to three short sentences explaining what was produced.",
        },
        "code": {
            "type": "string",
            "description": "Raw code to inject; empty string when no insertion is useful.",
        },
    },
    "required": ["spoken", "code"],
    "additionalProperties": False,
}


@dataclass(frozen=True)
class CodeResponse:
    spoken: str
    code: str
    raw_text: str


class AnthropicCodeBridge:
    """Bridge from a transcribed voice command to a structured {spoken, code} reply.

    Uses Claude via the Anthropic Messages API with `output_config.format` as a
    JSON schema, which guarantees the response parses cleanly without the
    fragile fence-stripping the previous OpenAI Responses path needed.
    """

    def __init__(self, config: AnthropicConfig):
        self.config = config
        self._client = None

    def generate(self, command: str) -> CodeResponse:
        client = self._load_client()

        output_config: dict[str, Any] = {
            "format": {"type": "json_schema", "schema": _REPLY_SCHEMA},
        }
        request: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_output_tokens,
            "system": self.config.system_prompt,
            "messages": [
                {"role": "user", "content": f"Voice command:\n{command.strip()}"}
            ],
            "output_config": output_config,
        }

        # Adaptive thinking is opt-in: voice flows are latency-sensitive, so
        # the default skips thinking entirely and emits the answer directly.
        # Flip `thinking_enabled` in config for hard problems where you'd
        # rather pay 1-3s of latency for better reasoning.
        if self.config.thinking_enabled:
            request["thinking"] = {"type": "adaptive"}
            if self.config.effort:
                output_config["effort"] = self.config.effort

        LOGGER.info("Sending voice command to Anthropic model=%s", self.config.model)
        response = client.messages.create(**request)

        # The schema-constrained output is always a single text block;
        # any thinking blocks (when enabled) come before it and we skip them.
        text = next((b.text for b in response.content if b.type == "text"), "")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            # output_config.format makes this practically impossible, but
            # degrade gracefully if the SDK ever returns malformed JSON.
            LOGGER.warning("Anthropic reply was not parseable JSON; treating as spoken")
            return CodeResponse(spoken=text, code="", raw_text=text)

        return CodeResponse(
            spoken=str(payload.get("spoken", "")).strip(),
            code=str(payload.get("code", "")).strip(),
            raw_text=text,
        )

    def _load_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic()
        return self._client
