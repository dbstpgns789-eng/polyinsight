# -*- coding: utf-8 -*-
"""인스타 캡션 생성 (Phase 0 반자동 발행, 2026-07-21).

덱 내용 → 인스타 게시용 캡션(진지한 논문요약형 + 짧은 출처 + 도달 해시태그).

★핵심 불변식 (해자의 마지막 마일): 캡션은 **공개로 나가는 새 텍스트**다. 캡션이 덱에 없는
수치를 지어내면 가장 공개적인 순간에 '검증' 약속이 깨진다. 그래서:
  - 캡션 수치는 덱의 **검증 통과 집합**(fidelity.verified_number_strings)에서만.
  - 생성 후 대조해 위반 수치가 있으면 **수치 없는 캡션으로 재생성**(수치 0이면 위반 불가).
  이러면 '캡션 미확인 수치 0'이 산술적으로 보장된다.

비용: 원문(paper_text)을 넣지 않는다 — 덱 텍스트 + 검증수치 + 출처만(작음). Sonnet 1콜.
lazy 생성이라 덱당 1회(라우터가 캐시). 원문 재전송 금지가 원가 방어의 핵심.
"""
from __future__ import annotations

import json
import logging
import re

from ...core import fidelity
from ...core.config import settings
from ...core.llm_client import llm_client

logger = logging.getLogger(__name__)

IG_CAPTION_MAX = 2200        # 인스타 캡션 총 글자수 상한(본문+해시태그 합산)
IG_HASHTAG_MAX = 30          # 인스타 해시태그 개수 상한
_TAG_CLEAN = re.compile(r"[^0-9A-Za-z가-힣_]")
_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.S)

_SYSTEM = """너는 학술 연구를 대중에게 알리는 카드뉴스의 인스타그램 캡션을 쓴다.

톤: 진지한 논문요약형. 연구 니치 브랜드 — 호들갑·과장·클릭베이트 금지.
목적: 대중이 이 연구와 연구실에 관심을 갖게 한다(논문 설명이 아니라 관심 유발).

캡션 구성:
1. 훅 1줄 — 덱의 핵심 발견(과장 없이, 궁금하게)
2. 평이한 요약 2~3문장 — 무엇을 알아냈나, 왜 중요한가
3. 출처 인용 — 덱에 나오는 저자·저널·연도를 짧게(예: "Ryu et al., Cellulose (2024)"). 전체 서지 아님.

해시태그: 도달·노출 최적화. 연구 주제 태그 + 관련 인기 태그를 넉넉히(한국어/영어 혼용 가능).

★수치 규칙(가장 중요): 아래 '사용 가능한 검증된 수치' 목록에 있는 수치만 써라.
목록에 없는 어떤 숫자도 캡션에 쓰지 마라. 애매하면 수치 없이 서술해라.

반드시 이 JSON만 출력(설명·마크다운 없이):
{"caption": "훅+요약+출처를 줄바꿈으로 구성한 본문", "hashtags": ["태그1", "태그2", ...]}"""

_SYSTEM_NO_NUM = _SYSTEM.replace(
    "★수치 규칙(가장 중요): 아래 '사용 가능한 검증된 수치' 목록에 있는 수치만 써라.\n"
    "목록에 없는 어떤 숫자도 캡션에 쓰지 마라. 애매하면 수치 없이 서술해라.",
    "★수치 규칙: 이번엔 **어떤 구체적 숫자도 쓰지 마라**. 정성적으로만 서술해라(예: '크게 늘었다').",
)


def _deck_text(html: str) -> str:
    """덱 HTML → 콘텐츠 텍스트(출처 인용 포함). CSS·스크립트·주석 제거."""
    return fidelity._content_text(html)[:6000]   # 덱 텍스트는 작다. 원문 아님(원가 방어).


def _parse(raw: str) -> tuple[str, list[str]]:
    """LLM 출력 → (caption, hashtags). 코드펜스·잡텍스트에 관대하게."""
    m = _FENCE.search(raw)
    body = m.group(1) if m else raw
    start = body.find("{")
    end = body.rfind("}")
    if start >= 0 and end > start:
        body = body[start:end + 1]
    data = json.loads(body)
    caption = str(data.get("caption", "")).strip()
    tags_raw = data.get("hashtags", []) or []
    tags = [_TAG_CLEAN.sub("", str(t)) for t in tags_raw]
    tags = [t for t in tags if t]                # 빈 태그 제거
    return caption, tags


def _fit_instagram(caption: str, hashtags: list[str]) -> tuple[str, list[str]]:
    """IG 상한 강제 — 해시태그 30개 이하, 본문+태그 합산 2200자 이하.

    넘으면 해시태그를 뒤에서 덜어낸다(본문이 캡션의 본질, 태그는 부속).
    프론트는 '캡션 + \\n\\n + #태그들'로 합치므로 그 길이 기준으로 맞춘다.
    """
    hashtags = hashtags[:IG_HASHTAG_MAX]
    while hashtags:
        combined = caption + "\n\n" + " ".join(f"#{t}" for t in hashtags)
        if len(combined) <= IG_CAPTION_MAX:
            break
        hashtags = hashtags[:-1]                 # 가장 뒤 태그부터 버린다
    return caption, hashtags


async def generate_caption(html: str, paper_text: str) -> dict:
    """덱 → {"caption": str, "hashtags": list[str]}. 미확인 수치 0 보장.

    1) 검증수치 제약으로 생성 → 2) 대조, 위반 있으면 수치 없는 캡션으로 재생성 → 3) IG 상한.
    """
    if settings.DEV_MOCK_LLM:
        return {"caption": "목업 캡션입니다. 연구 요약. Ryu et al. (2024)", "hashtags": ["연구", "research"]}

    verified = fidelity.verified_number_strings(html, paper_text)
    deck_text = _deck_text(html)
    nums = ", ".join(sorted(verified)) if verified else "(없음 — 수치 인용 자제)"
    user = f"덱 내용:\n{deck_text}\n\n사용 가능한 검증된 수치: {nums}"

    raw = await llm_client.call(
        system_prompt=_SYSTEM, user_prompt=user,
        max_tokens=1024, temperature=0.5, model=settings.LLM_MODEL_EDIT,
    )
    caption, hashtags = _parse(raw)

    ok, violations = fidelity.caption_numbers_ok(caption, verified)
    if not ok:
        # 위반 수치 존재 → 수치 없는 캡션으로 재생성(수치 0이면 위반 불가 = #2 산술 보장).
        logger.info("caption: 미확인 수치 %s → 수치 없는 캡션 재생성", violations)
        raw = await llm_client.call(
            system_prompt=_SYSTEM_NO_NUM, user_prompt=f"덱 내용:\n{deck_text}",
            max_tokens=1024, temperature=0.5, model=settings.LLM_MODEL_EDIT,
        )
        caption, hashtags = _parse(raw)

    caption, hashtags = _fit_instagram(caption, hashtags)
    return {"caption": caption, "hashtags": hashtags}
