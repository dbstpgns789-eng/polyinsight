# -*- coding: utf-8 -*-
"""크레딧 소진을 사람 말로 안내한다.

실전(2026-07-13): 크레딧이 떨어지자 유저에게 이런 게 떴다 —
  ERR-AUTHOR: Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error',
  'message': 'Your credit balance is too low to access the Anthropic API...'}}

박사님이 첫 논문을 올렸는데 이걸 보면 안 된다. **운영자가 고칠 문제를 유저 탓처럼 보이게 하는 건
최악의 에러 메시지다.** "지금은 만들 수 없습니다, 곧 복구됩니다"라고 말해야 한다.
"""
import pytest

from backend.core.llm_client import LLMCreditError, classify_api_error


def test_credit_message_is_detected():
    msg = ("Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', "
           "'message': 'Your credit balance is too low to access the Anthropic API. "
           "Please go to Plans & Billing to upgrade or purchase credits.'}}")
    exc = classify_api_error(msg, 400)
    assert isinstance(exc, LLMCreditError)


def test_credit_error_speaks_human():
    """유저에게는 사람 말로. 'credit balance'·'400' 같은 내부 사정을 보여주지 않는다.

    ('크레딧'이라는 단어조차 유저에겐 내부 용어다 — "AI 사용량 한도"가 더 낫다.)
    """
    text = str(LLMCreditError())
    assert "만들 수 없습니다" in text        # 무슨 일이 일어났는지
    assert "다시 시도" in text                # 무엇을 하면 되는지
    assert "credit" not in text.lower()      # 영문 원문 노출 금지
    assert "400" not in text                  # 상태 코드 노출 금지
    assert "{" not in text                    # JSON 스택트레이스 노출 금지


def test_other_errors_stay_generic():
    exc = classify_api_error("Error code: 500 - internal server error", 500)
    assert not isinstance(exc, LLMCreditError)


@pytest.mark.parametrize("msg", [
    "credit balance is too low",
    "Your Credit Balance Is Too Low",
    "insufficient credits",
])
def test_variants_detected(msg):
    assert isinstance(classify_api_error(msg, 400), LLMCreditError)
