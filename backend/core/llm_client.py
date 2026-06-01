from __future__ import annotations

import asyncio
import logging

import anthropic

from .config import settings

logger = logging.getLogger(__name__)


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
        self._client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        timeout_s: int = 120,
        stop_sequences: list[str] | None = None,
    ) -> str:
        # Haiku 4.5 max output: 8192 tokens
        capped_tokens = min(max_tokens, 8192)
        logger.info("LLM call | model=%s | prompt_len=%d | max_tokens=%d",
                    self.model, len(user_prompt), capped_tokens)

        kwargs: dict = dict(
            model=self.model,
            max_tokens=capped_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        if stop_sequences:
            kwargs["stop_sequences"] = stop_sequences

        try:
            message = await asyncio.wait_for(
                self._client.messages.create(**kwargs),
                timeout=timeout_s,
            )
        except anthropic.AuthenticationError as exc:
            raise LLMAuthError(str(exc)) from exc
        except anthropic.RateLimitError as exc:
            raise LLMRateLimitError(str(exc)) from exc
        except asyncio.TimeoutError as exc:
            raise LLMAPIError("timeout") from exc
        except anthropic.APIError as exc:
            raise LLMAPIError(str(exc), status_code=getattr(exc, "status_code", None)) from exc

        text = message.content[0].text if message.content else ""
        logger.info("LLM call done | input_tokens=%d | output_tokens=%d",
                    message.usage.input_tokens, message.usage.output_tokens)
        return text.strip()


llm_client = LLMClient()
