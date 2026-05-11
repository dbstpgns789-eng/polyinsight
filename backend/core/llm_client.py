from __future__ import annotations

import asyncio
import json
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
        self.provider = settings.LLM_PROVIDER
        if self.provider == "gemini":
            self.model = model or settings.GEMINI_MODEL
            self._gemini_key = settings.GEMINI_API_KEY
            if not self._gemini_key:
                raise LLMAuthError("GEMINI_API_KEY is not set")
        else:
            self.model = model or settings.LLM_MODEL
            if not settings.ANTHROPIC_API_KEY:
                raise LLMAuthError("ANTHROPIC_API_KEY is not set")
            self._client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def call(
        self,
        system_prompt: str | list[dict[str, Any]],
        user_prompt: str,
        max_tokens: int = 2048,
        temperature: float = 0.3,
        timeout_s: int = 60,
        stop_sequences: list[str] | None = None,
        response_schema: dict | None = None,
    ) -> str:
        if self.provider == "gemini":
            return await self._call_gemini(
                system_prompt, user_prompt, max_tokens, temperature, timeout_s, response_schema
            )
        return await self._call_anthropic(
            system_prompt, user_prompt, max_tokens, temperature, timeout_s, stop_sequences, response_schema
        )

    # ── Anthropic ────────────────────────────────────────────────────────────

    async def _call_anthropic(
        self,
        system_prompt: str | list[dict[str, Any]],
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        timeout_s: int,
        stop_sequences: list[str] | None,
        response_schema: dict | None,
    ) -> str:
        if response_schema is not None:
            return await self._call_anthropic_tool(
                system_prompt, user_prompt, max_tokens, temperature, timeout_s, response_schema
            )

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

    async def _call_anthropic_tool(
        self,
        system_prompt: str | list[dict[str, Any]],
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        timeout_s: int,
        response_schema: dict,
    ) -> str:
        # Force structured JSON output via tool_use
        tool: dict[str, Any] = {
            "name": "structured_output",
            "description": "Output the structured result according to the schema.",
            "input_schema": response_schema,
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": "structured_output"},
        }
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

        for block in response.content:
            if getattr(block, "type", None) == "tool_use":
                return json.dumps(block.input)
        raise LLMAPIError("Anthropic tool_use: no tool_use block in response")

    # ── Gemini ───────────────────────────────────────────────────────────────

    async def _call_gemini(
        self,
        system_prompt: str | list[dict[str, Any]],
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        timeout_s: int,
        response_schema: dict | None,
    ) -> str:
        try:
            import google.generativeai as genai  # lazy — optional dep
        except ImportError as exc:
            raise LLMAPIError(
                "google-generativeai not installed. Run: pip install google-generativeai"
            ) from exc

        if isinstance(system_prompt, str):
            system_str = system_prompt
        else:
            system_str = "\n".join(
                p.get("text", "") for p in system_prompt if p.get("type") == "text"
            )

        gen_config: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }
        if response_schema is not None:
            gen_config["response_mime_type"] = "application/json"
            gen_config["response_schema"] = response_schema

        genai.configure(api_key=self._gemini_key)
        model = genai.GenerativeModel(
            model_name=self.model,
            generation_config=genai.types.GenerationConfig(**gen_config),
            system_instruction=system_str or None,
        )

        try:
            response = await asyncio.wait_for(
                model.generate_content_async(user_prompt),
                timeout=timeout_s,
            )
        except asyncio.TimeoutError as exc:
            raise LLMAPIError("timeout") from exc
        except Exception as exc:
            msg = str(exc).lower()
            if "api_key" in msg or "authentication" in msg or "invalid" in msg:
                raise LLMAuthError(str(exc)) from exc
            if "quota" in msg or "rate" in msg:
                raise LLMRateLimitError(str(exc)) from exc
            raise LLMAPIError(str(exc)) from exc

        return response.text.strip()
