from __future__ import annotations

import asyncio
from typing import Any

import anthropic
from anthropic import AsyncAnthropic

from .config import settings


class LLMAuthError(Exception):
    pass


class LLMRateLimitError(Exception):
    pass


class LLMAPIError(Exception):
    def __init__(self, msg: str, status_code: int | None = None):
        super().__init__(msg)
        self.status_code = status_code


class LLMClient:
    def __init__(self, model: str | None = None) -> None:
        self.model = model or settings.LLM_MODEL
        self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def call(
        self,
        system_prompt: str | list[dict[str, Any]],
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        timeout_s: int = 60,
        stop_sequences: list[str] | None = None,
    ) -> str:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        if stop_sequences is not None:
            payload["stop_sequences"] = stop_sequences

        try:
            response = await asyncio.wait_for(
                self._client.messages.create(**payload),
                timeout=timeout_s,
            )
        except anthropic.AuthenticationError as exc:
            raise LLMAuthError(str(exc)) from exc
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
        except anthropic.APIStatusError as exc:
            raise LLMAPIError(str(exc), status_code=exc.status_code) from exc
        except asyncio.TimeoutError as exc:
            raise LLMAPIError("timeout") from exc

        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts).strip()
