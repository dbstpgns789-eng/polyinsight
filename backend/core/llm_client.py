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


class LLMTruncationError(Exception):
    """출력이 max_tokens 천장에서 잘림. 동일 입력·저온이면 재시도해도 같은 결과이므로
    호출자는 재시도하지 말고 입력(예: 카드 수)을 줄여야 한다."""

    def __init__(self, output_tokens: int, max_tokens: int):
        self.output_tokens = output_tokens
        self.max_tokens = max_tokens
        super().__init__(
            f"output truncated at max_tokens ceiling "
            f"(output_tokens={output_tokens}, max_tokens={max_tokens})"
        )


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
        model: str | None = None,
    ) -> str:
        # per-call 모델 오버라이드 (없으면 인스턴스 기본). 팀별 라우팅용.
        resolved = model or self.model
        # 출력 천장은 모델별로 다르다. Haiku 4.5 = 8192(이 천장이 ERR-S6-002 트리거).
        # Sonnet 등은 더 큰 출력 허용 → 천장 완화.
        ceiling = 8192 if resolved.startswith("claude-haiku") else 64000
        capped_tokens = min(max_tokens, ceiling)
        logger.info("LLM call | model=%s | prompt_len=%d | max_tokens=%d",
                    resolved, len(user_prompt), capped_tokens)

        kwargs: dict = dict(
            model=resolved,
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
        logger.info("LLM call done | input_tokens=%d | output_tokens=%d | stop_reason=%s",
                    message.usage.input_tokens, message.usage.output_tokens, message.stop_reason)

        # 출력이 천장에서 잘리면 JSON이 미완성 → 재시도 무의미. 호출자에게 명확히 신호.
        if message.stop_reason == "max_tokens":
            raise LLMTruncationError(message.usage.output_tokens, capped_tokens)

        return text.strip()


llm_client = LLMClient()
