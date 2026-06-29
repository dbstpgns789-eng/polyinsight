from __future__ import annotations

import asyncio
import contextvars
import logging

import anthropic

from .config import settings

logger = logging.getLogger(__name__)


# ── per-job LLM 사용량 집계 (행동/비용 로깅용) ──────────────────────────────
# 오케스트레이터가 job 시작 시 start_usage_capture()로 버킷을 설정하고,
# 각 LLM call()이 같은 버킷(가변 dict)에 토큰을 누적한다. asyncio 태스크가
# 버킷 설정 이후 생성되면 ContextVar가 같은 dict 참조를 상속한다.
_usage_var: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "llm_usage", default=None
)


def start_usage_capture() -> dict:
    bucket = {"input_tokens": 0, "output_tokens": 0, "calls": 0}
    _usage_var.set(bucket)
    return bucket


def get_usage() -> dict | None:
    return _usage_var.get()


def _record_usage(input_tokens: int, output_tokens: int) -> None:
    bucket = _usage_var.get()
    if bucket is not None:
        bucket["input_tokens"] += input_tokens
        bucket["output_tokens"] += output_tokens
        bucket["calls"] += 1


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

    async def _stream_final(self, kwargs: dict):
        """streaming으로 받아 최종 Message(usage·stop_reason·content 포함) 반환.
        SDK는 max_tokens가 커서 >10분 가능하면 비스트리밍을 거부 → 대용량 저작은 stream=True."""
        async with self._client.messages.stream(**kwargs) as s:
            return await s.get_final_message()

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.3,
        timeout_s: int = 120,
        stop_sequences: list[str] | None = None,
        model: str | None = None,
        stream: bool = False,
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
            if stream:
                message = await asyncio.wait_for(self._stream_final(kwargs), timeout=timeout_s)
            else:
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
        # 잘림 여부와 무관하게 실제 발생한 토큰을 집계 (비용 가시화).
        _record_usage(message.usage.input_tokens, message.usage.output_tokens)

        # 출력이 천장에서 잘리면 JSON이 미완성 → 재시도 무의미. 호출자에게 명확히 신호.
        if message.stop_reason == "max_tokens":
            raise LLMTruncationError(message.usage.output_tokens, capped_tokens)

        return text.strip()


llm_client = LLMClient()
