from __future__ import annotations

import asyncio
import time
import logging

from google import genai
from google.genai import types

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


# ── 전역 Rate Limiter ────────────────────────────────────────────────────────
# Gemini 무료 티어: 15 RPM / 1,500 RPD
# Semaphore(1): 동시 호출 1개만 허용
# MIN_INTERVAL_S: 호출 간 최소 4초 대기 → 실질 최대 15 RPM 이하 유지
_llm_semaphore = asyncio.Semaphore(1)
_MIN_INTERVAL_S: float = 4.0          # 초당 호출 간격 하한
_last_call_time: float = 0.0          # 마지막 호출 완료 시각

# 일일 호출 카운터 (프로세스 재시작 시 리셋 — 간단한 보호용)
_daily_call_count: int = 0
_daily_reset_date: str = ""
MAX_DAILY_CALLS: int = 200            # 1,500 RPD의 안전 마진 (13%)


async def _throttle() -> None:
    """호출 간 최소 간격 보장."""
    global _last_call_time
    elapsed = time.monotonic() - _last_call_time
    if elapsed < _MIN_INTERVAL_S:
        wait = _MIN_INTERVAL_S - elapsed
        logger.debug("LLM throttle: waiting %.1fs", wait)
        await asyncio.sleep(wait)


def _check_daily_limit() -> None:
    """일일 호출 한도 초과 시 예외."""
    global _daily_call_count, _daily_reset_date
    today = time.strftime("%Y-%m-%d")
    if _daily_reset_date != today:
        _daily_call_count = 0
        _daily_reset_date = today
    if _daily_call_count >= MAX_DAILY_CALLS:
        raise LLMRateLimitError(
            f"Daily LLM call limit reached ({MAX_DAILY_CALLS}/day). "
            "Resets at midnight."
        )


# ── LLMClient ────────────────────────────────────────────────────────────────

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
        global _last_call_time, _daily_call_count

        # 일일 한도 확인
        _check_daily_limit()

        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens,
            stop_sequences=stop_sequences or [],
        )

        # Semaphore 획득 → 직렬화 보장
        async with _llm_semaphore:
            await _throttle()

            logger.info(
                "LLM call #%d | model=%s | prompt_len=%d",
                _daily_call_count + 1,
                self.model,
                len(user_prompt),
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
            finally:
                _last_call_time = time.monotonic()

            _daily_call_count += 1
            logger.info("LLM call done | daily_total=%d", _daily_call_count)

        return (response.text or "").strip()

    @staticmethod
    def usage_stats() -> dict:
        """현재 호출 통계 반환 (디버그/모니터링용)."""
        return {
            "daily_calls": _daily_call_count,
            "daily_limit": MAX_DAILY_CALLS,
            "remaining": MAX_DAILY_CALLS - _daily_call_count,
            "min_interval_s": _MIN_INTERVAL_S,
        }


llm_client = LLMClient()
