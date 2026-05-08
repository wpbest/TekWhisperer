from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from .config import OpenAIConfig

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CodeResponse:
    spoken: str
    code: str
    raw_text: str


class OpenAICodeBridge:
    def __init__(self, config: OpenAIConfig):
        self.config = config
        self._client = None

    def generate(self, command: str) -> CodeResponse:
        client = self._load_client()
        request: dict[str, Any] = {
            "model": self.config.model,
            "input": [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": f"Voice command:\n{command.strip()}"},
            ],
            "max_output_tokens": self.config.max_output_tokens,
        }
        if self.config.reasoning_effort and self.config.reasoning_effort.lower() != "none":
            request["reasoning"] = {"effort": self.config.reasoning_effort}

        LOGGER.info("Sending voice command to OpenAI model=%s", self.config.model)
        response = client.responses.create(**request)
        text = _response_to_text(response)
        parsed = _parse_response(text)
        return CodeResponse(spoken=parsed["spoken"], code=parsed["code"], raw_text=text)

    def _load_client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI()
        return self._client


def _response_to_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)

    chunks: list[str] = []
    for item in getattr(response, "output", []) or []:
        for content in getattr(item, "content", []) or []:
            text = getattr(content, "text", None)
            if text:
                chunks.append(str(text))
    return "\n".join(chunks).strip()


def _parse_response(text: str) -> dict[str, str]:
    candidate = _strip_code_fence(text.strip())
    try:
        payload = json.loads(candidate)
    except json.JSONDecodeError:
        LOGGER.warning("OpenAI response was not JSON; treating it as spoken text")
        return {"spoken": candidate, "code": ""}

    return {
        "spoken": str(payload.get("spoken", "")).strip(),
        "code": str(payload.get("code", "")).strip(),
    }


def _strip_code_fence(text: str) -> str:
    if not text.startswith("```"):
        return text

    lines = text.splitlines()
    if len(lines) >= 3 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return text
