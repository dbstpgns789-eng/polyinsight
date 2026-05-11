from __future__ import annotations

import asyncio
from typing import Any

from google import genai
from google.genai import types

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
        self._client = genai.Client(api_key=settings.GEMINI_API_KEY)

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        timeout_s: int = 60,
        stop_sequences: list[str] | None = None,
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
            stop_sequences=stop_sequences or [],
        )

        try:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=config,
                ),
                timeout=timeout_s,
            )
        except Exception as exc:
            msg = str(exc)
            if "API_KEY_INVALID" in msg or "UNAUTHENTICATED" in msg:
                raise LLMAuthError(msg) from exc
            if "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower():
                raise LLMRateLimitError(msg) from exc
            if isinstance(exc, asyncio.TimeoutError):
                raise LLMAPIError("timeout") from exc
            raise LLMAPIError(msg) from exc

        return (response.text or "").strip()


llm_client = LLMClient()
