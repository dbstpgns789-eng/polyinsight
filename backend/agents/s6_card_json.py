from __future__ import annotations

import asyncio
import json
import logging
import re

from .base import BaseAgent
from ..core.config import settings
from ..core.llm_client import llm_client, LLMTruncationError
from ..core.models import (
    CardEditorData, CardMeta, CardSlot, FieldValue,
    MatchQuality, RiskLevel, ClaimType, FieldSource,
    CardStorybeat, Storyboard,
    S6Input, S6Output,
    THEME_PRESETS,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 템플릿별 필드 명세 (LLM에게 전달)
# ---------------------------------------------------------------------------

_TEMPLATE_SPEC = """
[cover_v2]    표지 (첫 카드)
  필드: eyebrow(시리즈/권호 한 줄), headline(핵심 주제, 강조어를 *별표*로 감쌈),
        subtitle(한 줄 부제), org(기관명)

[statement]   문제 제기 / 기존 한계
  필드: eyebrow(섹션 라벨), headline(독자를 끄는 큰 질문, *별표* 강조),
        body(문제·한계 2~3문장)

[feature]     핵심 혁신
  필드: eyebrow, headline(혁신 한 줄, *별표* 강조), body(혁신 설명 2~3문장)

[process_v2]  제작 방법
  필드: eyebrow, headline(공정 제목),
        steps("단계1|단계2|단계3" — |로 구분, 3~5단계), caption(보조 한 줄)

[bigstat_compare]  핵심 성능 + 기존 대비 + 출처
  필드: eyebrow, headline(*별표* 강조),
        stat_value(대표 수치 숫자만), stat_unit(단위), stat_caption(수치 맥락 한 줄),
        bars("라벨:값:강조" — |로 항목 구분, :로 쌍 구분, 강조는 1(우리/최고) 또는 0; 2~4행),
        source_ref(출처 — "출처: 저널(연도) · 섹션")

[reasons]     왜 이 소재인가
  필드: eyebrow, headline(*별표* 강조),
        reasons("제목:본문|제목:본문" — |로 항목, :로 제목·본문 구분; 2~4개)

[grid_v2]     응용 분야
  필드: eyebrow, headline(*별표* 강조),
        items("라벨:서브|라벨:서브" — |로 항목, :로 라벨·서브 구분; 2~4개),
        body(선택 요약 한 줄)

[closing_v2]  마무리 / 협력 (마지막 카드)
  필드: eyebrow, headline(*별표* 강조), body(마무리 2~3문장), source_ref(선택)

[포맷 규칙 — 엄수]
- headline 강조: 핵심어를 *별표*로 감싼다 (예: 기존보다 *더 단단*하다). 1곳 권장.
- 다항목 필드: 항목 구분 |, 쌍 구분 :. 라벨/값 내부에 |·: 사용 금지.
- bars 3번째 토큰은 1(강조행, 보통 최댓값/우리 방식) 또는 0.
- 수치(stat_value·bars)는 원문에서만, source 필수.
"""

# ---------------------------------------------------------------------------
# 템플릿 배치 규칙
# ---------------------------------------------------------------------------

_SEQUENCING_RULES = """
실험형 논문 서사 가이드 (soft — 강제 표가 아니라 AI가 논문·card_count에 맞게 취사):
- 첫 카드: [cover_v2] (표지)
- 마지막 카드: [closing_v2] (마무리)
- 가능하면 포함: [feature](혁신), [bigstat_compare](핵심 성능 — KITECH 성능 중심)
- 선택(논문에 있으면): [statement](훅/한계), [reasons](왜 이 소재),
  [process_v2](제작 단계), [grid_v2](응용)
- card_count 장에 맞게 storyboard에서 뼈대 조합을 직접 결정한다.
- 같은 뼈대 연속·중복 지양. 내러티브: 표지 → 문제/혁신 → 성능 → 응용 → 마무리.
- 8뼈대 모두 선택지다. 논문 내용이 있으면 reasons·process_v2·grid_v2도 적극 활용한다.
"""

# ---------------------------------------------------------------------------
# 프롬프트
# ---------------------------------------------------------------------------

_SYSTEM = """당신은 학술 논문을 인스타그램 카드뉴스로 변환하는 전문가입니다.
당신의 역할: 전체 스토리를 기획하고 디자인 결정(템플릿 선택)을 내린다.
사용자는 결과를 검토하고 수정할 권한을 가진다.

독자 페르소나:
- 일반인 50%: 비전공자 — 논문은 안 읽지만 주제에 호기심 있는 사람
- 관련분야 50%: 준전문가 — 분야는 알지만 논문 구조를 따라가기 어려운 사람
- 채널: 인스타그램 (스크롤 중 2~3초 안에 흥미를 잡아야 함)

가독성 원칙 (수치를 왜곡하지 않으면서 쉽게 풀어쓰는 것은 fidelity 위반이 아니다):
A. 영어 약어는 첫 등장 시 반드시 한글로 풀어 쓴다 (예: IPA → 중요도-성취도 분석(IPA))
B. 수치는 맥락과 함께 제시한다 (예: 77.9% → 응답자 10명 중 8명(77.9%))
C. 각 카드는 메시지 하나. 문장은 짧고 구어체로 (종결어미: ~다 대신 ~네요, ~이에요 사용 가능)
D. 전문 용어를 쓸 때는 독자가 이해할 수 있는 한 줄 설명을 괄호 안에 붙인다

핵심 원칙:
1. section_map(원문)에서만 사실을 추출한다.
2. 수치(숫자, %, 배율)는 반드시 원문에서 찾아야 한다.
3. 원문에 없는 내용은 절대 만들지 않는다.
4. 찾을 수 없으면 value="" + match_quality="failed"로 표기한다.

작성 순서 (Storyboard-first):
1. SEARCH     — 원문에서 핵심 구절 위치 파악 (페이지 마커로 특정)
2. STORYBOARD — 전체 스토리 계획을 먼저 확정한다
               - card_count장의 narrative_role, template_type, key_message를 모두 결정
               - JSON의 "storyboard" 필드를 cards보다 먼저 작성한다
               - 같은 템플릿 연속 사용 지양, 내러티브 다양성 확보
3. WRITE      — storyboard.beats를 참고해 각 카드 fields를 원문에서 추출
               - cards[n].template_type은 storyboard.beats[n].template_type과 반드시 일치
4. SCORE      — confidence/match_quality/risk_level 판정

FieldValue 구조:
{
  "value": "텍스트",
  "confidence": "high|medium|low",
  "match_quality": "exact|normalized|fuzzy|semantic|failed",
  "claim_type": "quantitative|qualitative|causal",
  "source": {"section": "섹션명", "page": 1}
}
(risk_level·verified는 출력하지 마라 — 코드가 match_quality·claim_type을 보고 자동 판정한다.)

필드 포맷 규칙 (신규 뼈대):
- headline의 핵심어는 *별표*로 감싼다 (렌더 시 강조색). 예: 기존보다 *더 단단*하다
- 다항목 필드(bars·steps·reasons·items)는 항목 구분 |, 쌍 구분 :를 쓴다.
  · bars: "라벨:값:강조(1/0)"  · steps: "단계1|단계2|단계3"
  · reasons: "제목:본문|..."   · items: "라벨:서브|..."
- 라벨/값 내부에 | 또는 : 를 쓰지 않는다.

recommended_theme — 논문 연구 분야에 따라 정확히 하나를 선택:
tech_blue: AI·ML·컴퓨터·네트워크·센서·전자
forest_green: 바이오·화학·폴리머·재료·식품·농업·환경
sunset_orange: 에너지·배터리·기계·제조·로봇
royal_violet: 의료·임상·건강·약학
golden_yellow: 경제·정책·사회·혁신
slate: 기타

반환: JSON만. 설명 없음."""

_USER = """## 논문 원문

{section_map_text}

---
제목: {title}
저자: {authors}
연도: {year}
기관: {org}

---
## 사용 가능한 템플릿

{template_spec}

{sequencing_rules}

---
## 지시

카드 {card_count}장짜리 카드뉴스를 작성하라.

**반드시 storyboard를 먼저 완성한 뒤 cards를 작성하라.**
storyboard.beats에서 모든 카드의 template_type을 확정하고,
cards 배열은 그 계획을 따른다.

아래 JSON 스키마를 완성하라:

{{
  "recommended_theme": "tech_blue",
  "storyboard": {{
    "story_arc": "전체 스토리 한 문장 요약",
    "beats": [
      {{
        "card_num": 1,
        "template_type": "템플릿명",
        "narrative_role": "이 카드가 전체 스토리에서 맡는 역할",
        "key_message": "이 카드에서 전달할 핵심 메시지 한 줄"
      }},
      ... (총 {card_count}개)
    ]
  }},
  "meta": {{
    "org":            <FieldValue>,
    "dept":           <FieldValue>,
    "researcher":     <FieldValue>,
    "month":          <FieldValue>,
    "edition_number": <FieldValue>
  }},
  "cards": [
    {{
      "card_num": 1,
      "template_type": "템플릿명",
      "fields": {{
        "필드명": <FieldValue>,
        ...
      }}
    }},
    ... (총 {card_count}개)
  ]
}}"""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

def _make_fv(
    value: str,
    *,
    section: str = "abstract",
    page: int = 1,
    risk: str = "LOW",
    quality: str = "exact",
    claim: str = "qualitative",
    confidence: str = "high",
) -> FieldValue:
    return FieldValue(
        value=value,
        confidence=confidence,       # type: ignore[arg-type]
        match_quality=MatchQuality(quality),
        claim_type=ClaimType(claim),
        source=FieldSource(section=section, page=page),
        risk_level=RiskLevel(risk),
    )


# card_count → 대표 시퀀스 (mock 결정적; 실제 LLM은 AI가 storyboard로 선택).
# 아크 정합: 첫=cover_v2, 끝=closing_v2, bigstat_compare 포함.
_MOCK_SEQUENCES: dict[int, list[str]] = {
    3: ["cover_v2", "bigstat_compare", "closing_v2"],
    4: ["cover_v2", "feature", "bigstat_compare", "closing_v2"],
    5: ["cover_v2", "statement", "feature", "bigstat_compare", "closing_v2"],
    6: ["cover_v2", "statement", "feature", "bigstat_compare", "grid_v2", "closing_v2"],
    7: ["cover_v2", "statement", "feature", "process_v2", "bigstat_compare", "grid_v2", "closing_v2"],
}


def _mock_sequence(card_count: int) -> list[str]:
    if card_count in _MOCK_SEQUENCES:
        return _MOCK_SEQUENCES[card_count]
    base = _MOCK_SEQUENCES[7]
    if card_count < 3:
        return _MOCK_SEQUENCES[3]
    if card_count <= 7:
        mid = base[1:-1][: card_count - 2]
        return ["cover_v2", *mid, "closing_v2"]
    return base

_MOCK_FIELDS: dict[str, dict[str, FieldValue]] = {
    "cover_v2": {
        "eyebrow":  _make_fv("KITECH Research Note · 2026", quality="normalized"),
        "headline": _make_fv("플라스틱을 *대체*하는 셀룰로스 미세구슬"),
        "subtitle": _make_fv("COF 복합화로 강도와 생분해성을 동시에", section="abstract", page=1),
        "org":      _make_fv("KITECH 친환경소재연구부문"),
    },
    "statement": {
        "eyebrow":  _make_fv("문제 제기"),
        "headline": _make_fv("왜 친환경 플라스틱은 *약할*까?", section="introduction", page=2),
        "body":     _make_fv(
            "생분해성 소재는 대개 강도가 낮아 구조재로 쓰기 어렵다. 이 한계가 상용화를 막아 왔다.",
            section="introduction", page=2, confidence="medium",
        ),
    },
    "feature": {
        "eyebrow":  _make_fv("핵심 혁신"),
        "headline": _make_fv("셀룰로스에 *COF*를 짜 넣다", section="methods", page=4),
        "body":     _make_fv(
            "공유결합 유기골격체(COF)를 셀룰로스 매트릭스에 복합해, 미세구슬 형태로 강도와 다공성을 함께 얻었다.",
            section="methods", page=4,
        ),
    },
    "process_v2": {
        "eyebrow":  _make_fv("제작 방법"),
        "headline": _make_fv("세 단계로 만든다", section="methods", page=5),
        "steps":    _make_fv(
            "셀룰로스 용액에 COF 전구체 분산|에멀전법으로 미세구슬 성형|동결건조로 다공 구조 고정",
            section="methods", page=5,
        ),
        "caption":  _make_fv("전 과정 무용매·저온 — 친환경 공정", confidence="medium"),
    },
    "bigstat_compare": {
        "eyebrow":      _make_fv("성능 검증"),
        "headline":     _make_fv("기존 플라스틱보다 *더 단단*하다"),
        "stat_value":   _make_fv("238", section="results", page=7,
                                 quality="exact", claim="quantitative"),
        "stat_unit":    _make_fv("MPa"),
        "stat_caption": _make_fv("셀룰로스–COF 복합 미세구슬의 압축 강도", section="results", page=7),
        "bars":         _make_fv(
            "우리 복합 구슬:238:1|폴리프로필렌(PP):199:0|무보강 셀룰로스:142:0",
            section="results", page=7, quality="exact", claim="quantitative",
        ),
        "source_ref":   _make_fv("출처: Cellulose (2024) · Results", section="results", page=7),
    },
    "reasons": {
        "eyebrow":  _make_fv("왜 이 소재인가"),
        "headline": _make_fv("셀룰로스를 고른 *세 가지* 이유"),
        "reasons":  _make_fv(
            "풍부함:지구상 가장 많은 천연 고분자, 원료 걱정이 없다"
            "|생분해성:토양·해양에서 완전 분해된다"
            "|기능화 용이:표면 -OH로 COF 결합이 쉽다",
            section="introduction", page=3,
        ),
    },
    "grid_v2": {
        "eyebrow":  _make_fv("응용 분야"),
        "headline": _make_fv("어디에 *쓰일까*?"),
        "items":    _make_fv(
            "포장재:일회용 플라스틱 대체|흡착소재:중금속·염료 제거"
            "|약물전달:다공성 캡슐|단열재:경량 구조재",
            section="discussion", page=10,
        ),
        "body":     _make_fv("강도·다공성·생분해성의 조합이 응용 폭을 넓힌다.", confidence="medium"),
    },
    "closing_v2": {
        "eyebrow":    _make_fv("맺음말"),
        "headline":   _make_fv("다음은 *대량 생산* 검증", section="conclusion", page=12),
        "body":       _make_fv(
            "실험실 성과를 파일럿 규모로 확장해 경제성과 균일도를 확인하는 후속 연구를 진행한다.",
            section="conclusion", page=12,
        ),
        "source_ref": _make_fv("출처: Cellulose (2024) · Conclusion", section="conclusion", page=12),
    },
}


def _build_mock_card_data(
    card_count: int,
    section_map: dict[str, str],
    paper_metadata,
) -> CardEditorData:
    """DEV_MOCK_LLM 모드용 — 신규 8뼈대 결정적 시퀀스."""
    title = getattr(paper_metadata, "title", "") or "연구 성과"
    authors = getattr(paper_metadata, "authors", []) or []
    year = getattr(paper_metadata, "year", 2024) or 2024
    fv = _make_fv

    meta = CardMeta(
        org=fv("한국생산기술연구원"),
        dept=fv("친환경소재연구부문"),
        researcher=fv(authors[0] if authors else "연구팀"),
        month=fv(f"{year}-01", quality="normalized"),
        edition_number=fv(f"{year}-01호", quality="normalized"),
    )

    sequence = _mock_sequence(card_count)

    cards = [
        CardSlot(
            card_num=i + 1,
            template_type=tmpl,
            fields=_MOCK_FIELDS.get(tmpl, {"headline": fv(title)}),
        )
        for i, tmpl in enumerate(sequence)
    ]

    _ROLE_MAP = {
        "cover_v2": "논문 주제 표지",
        "statement": "문제 제기 / 기존 한계",
        "feature": "핵심 혁신 소개",
        "process_v2": "제작 방법 단계",
        "bigstat_compare": "핵심 성능 + 기존 대비 + 출처",
        "reasons": "왜 이 소재인가",
        "grid_v2": "응용 분야",
        "closing_v2": "마무리 / 협력",
    }
    storyboard = Storyboard(
        story_arc=f"{title}의 배경·혁신·성능·응용을 {len(cards)}장으로 구성",
        beats=[
            CardStorybeat(
                card_num=i + 1,
                template_type=tmpl,
                narrative_role=_ROLE_MAP.get(tmpl, "내용 전달"),
                key_message=_MOCK_FIELDS.get(tmpl, {}).get(
                    "headline", fv(title)
                ).value,
            )
            for i, tmpl in enumerate(sequence)
        ],
    )

    return CardEditorData(
        storyboard=storyboard, meta=meta, cards=cards,
        theme=THEME_PRESETS["forest_green"],
        recommended_theme_key="forest_green",
    )


class S6CardJsonAgent(BaseAgent[S6Input, S6Output]):
    """S6: section_map + card_count → CardEditorData (가변 CardSlot 리스트)."""

    MAX_RETRIES = 5
    SECTION_MAX_CHARS = 50000
    # 503 서버 과부하 시 대기 시간 (초): 1차 30s, 2차 60s, 3차 120s ...
    _503_BACKOFF = [30, 60, 120, 180]

    async def execute(self, input_data: S6Input) -> S6Output:
        if settings.DEV_MOCK_LLM:
            logger.info("S6: DEV_MOCK_LLM=True — LLM 호출 건너뜀, mock 데이터 반환")
            card_data = _build_mock_card_data(
                input_data.card_count,
                input_data.section_map,
                input_data.paper_metadata,
            )
            return S6Output(
                card_data=card_data,
                critical_count=self._count_risk(card_data, RiskLevel.CRITICAL),
                high_count=self._count_risk(card_data, RiskLevel.HIGH),
            )

        section_map_text = self._format_section_map(input_data.section_map)
        meta = input_data.paper_metadata

        user_prompt = _USER.format(
            section_map_text=section_map_text,
            title=meta.title or "unknown",
            authors=", ".join(meta.authors) if meta.authors else "unknown",
            year=meta.year or "unknown",
            org=", ".join(meta.authors[:1]) if meta.authors else "unknown",
            template_spec=_TEMPLATE_SPEC,
            sequencing_rules=_SEQUENCING_RULES,
            card_count=input_data.card_count,
        )

        last_exc: Exception | None = None
        for attempt in range(self.MAX_RETRIES):
            try:
                raw = await llm_client.call(
                    system_prompt=_SYSTEM,
                    user_prompt=user_prompt,
                    max_tokens=16000,
                    temperature=0.2,
                    timeout_s=120,
                )
                parsed = json.loads(self._extract_json(raw))
                card_data = self._build_card_editor_data(parsed)
                card_data = self._post_process(card_data)
                critical = self._count_risk(card_data, RiskLevel.CRITICAL)
                high = self._count_risk(card_data, RiskLevel.HIGH)
                logger.info(
                    "S6: done. cards=%d CRITICAL=%d HIGH=%d",
                    len(card_data.cards), critical, high,
                )
                return S6Output(
                    card_data=card_data,
                    critical_count=critical,
                    high_count=high,
                )
            except LLMTruncationError as exc:
                # 출력 천장 도달 — 재시도해도 동일 입력·저온이라 매번 같은 위치에서 잘림.
                # 즉시 중단하고 카드 수를 줄이라는 명확한 에러를 올린다.
                logger.error(
                    "S6: 출력 천장 도달 (output_tokens=%d/max=%d) — card_count=%d 과다",
                    exc.output_tokens, exc.max_tokens, input_data.card_count,
                )
                raise RuntimeError(
                    f"ERR-S6-002: 카드 {input_data.card_count}장이 모델 출력 한계"
                    f"({exc.max_tokens} 토큰)를 초과해 JSON이 잘렸습니다. "
                    f"카드 수를 줄이거나 더 큰 출력 모델이 필요합니다."
                ) from exc
            except Exception as exc:
                last_exc = exc
                logger.warning("S6: attempt %d failed — %s", attempt + 1, exc)
                if "503" in str(exc) and attempt < self.MAX_RETRIES - 1:
                    wait = self._503_BACKOFF[min(attempt, len(self._503_BACKOFF) - 1)]
                    logger.info("S6: 503 서버 과부하 — %ds 대기 후 재시도", wait)
                    await asyncio.sleep(wait)

        raise RuntimeError(f"ERR-S6-001: {last_exc}")

    # ── 파싱 ──────────────────────────────────────────────────────────────────

    def _build_card_editor_data(self, parsed: dict) -> CardEditorData:
        # storyboard 파싱 (없으면 None)
        storyboard: Storyboard | None = None
        if raw_sb := parsed.get("storyboard"):
            beats = [CardStorybeat.model_validate(b) for b in raw_sb.get("beats", [])]
            storyboard = Storyboard(story_arc=raw_sb.get("story_arc", ""), beats=beats)

        meta = CardMeta.model_validate(parsed["meta"])
        cards: list[CardSlot] = []
        for raw_card in parsed["cards"]:
            fields = {
                k: FieldValue.model_validate(v)
                for k, v in raw_card["fields"].items()
            }
            cards.append(CardSlot(
                card_num=raw_card["card_num"],
                template_type=raw_card["template_type"],
                fields=fields,
            ))

        raw_key = parsed.get("recommended_theme", "tech_blue")
        theme_key = raw_key if raw_key in THEME_PRESETS else "tech_blue"
        theme = THEME_PRESETS[theme_key]

        return CardEditorData(
            storyboard=storyboard, meta=meta, cards=cards,
            theme=theme, recommended_theme_key=theme_key,
        )

    # ── 후처리 ────────────────────────────────────────────────────────────────

    @staticmethod
    def _post_process(card_data: CardEditorData) -> CardEditorData:
        """verified 강제 False + risk_level 규칙 재판정."""
        for fv in _iter_field_values(card_data):
            fv.verified = False
            if (fv.claim_type == ClaimType.QUANTITATIVE
                    and fv.match_quality == MatchQuality.FAILED):
                fv.risk_level = RiskLevel.CRITICAL
            elif fv.match_quality in (MatchQuality.FUZZY, MatchQuality.SEMANTIC):
                fv.risk_level = RiskLevel.HIGH
            elif fv.match_quality == MatchQuality.NORMALIZED:
                fv.risk_level = RiskLevel.MEDIUM
            else:
                fv.risk_level = RiskLevel.LOW
        return card_data

    @staticmethod
    def _count_risk(card_data: CardEditorData, level: RiskLevel) -> int:
        return sum(1 for fv in _iter_field_values(card_data) if fv.risk_level == level)

    # ── 텍스트 헬퍼 ───────────────────────────────────────────────────────────

    def _format_section_map(self, section_map: dict[str, str]) -> str:
        parts = []
        total = 0
        for section, text in section_map.items():
            chunk = f"### {section}\n{text}"
            if total + len(chunk) > self.SECTION_MAX_CHARS:
                remaining = self.SECTION_MAX_CHARS - total
                if remaining > 200:
                    parts.append(chunk[:remaining] + "\n[truncated]")
                break
            parts.append(chunk)
            total += len(chunk)
        return "\n\n".join(parts)

    @staticmethod
    def _extract_json(text: str) -> str:
        m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if m:
            return m.group(1)
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return m.group(0)
        return text


def _iter_field_values(card_data: CardEditorData):
    """CardEditorData의 모든 FieldValue를 순회."""
    for fv in vars(card_data.meta).values():
        if isinstance(fv, FieldValue):
            yield fv
    for slot in card_data.cards:
        yield from slot.fields.values()


s6_agent = S6CardJsonAgent()
