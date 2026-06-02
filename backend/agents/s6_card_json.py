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
[cover]       표지
  필드: title(논문 핵심 주제 2~4줄), subtitle(한 줄 부제), edition(발행 시리즈/권호)

[hook]        문제 제기
  필드: title(독자를 끌어당기는 질문형 제목), highlight(핵심 키워드 2~4단어),
        body(문제 상황 2~3문장), source_credit(출처 기관·연도)

[problem]     연구 과제
  필드: title(해결해야 할 과제명), body(기존 기술의 한계 2~3문장),
        emphasis(연구팀이 선택한 돌파구 한 문장)

[circle3]     3요소 구조
  필드: title(전체 제목), body(3요소 통합 설명 2문장),
        c1·c2·c3 각각 "제목:라벨:서브" 형식 (예: "CVD 공정:핵심 기술:온도 700°C")

[compare2]    비교 분석
  필드: title(비교 제목), subtitle(비교 관점),
        label_a(기존 방식 명칭), points_a("항목1·항목2·항목3" — ·로 구분, 3~4개),
        label_b(신기술 명칭), points_b(동일 형식)

[grid4]       4분할 소개
  필드: title, subtitle,
        item1_label~item4_label(각 항목 제목), item1_sub~item4_sub(각 항목 설명 한 줄)

[definition]  용어 정의
  필드: term(핵심 용어), term_detail(영문명·풀네임 등),
        definition_text(정의 한 문장), body(의미·중요성 2~3문장)

[flow]        프로세스 순서
  필드: title(공정/단계 제목),
        steps_text("단계1·단계2·단계3" — ·로 구분, 4~6단계)

[data]        수치 시각화
  필드: title(차트 제목), data_unit(단위 설명),
        bars("레이블1:값1|레이블2:값2" — |로 구분, 4~6개),
        bar_max(bars 중 최대값, 숫자만), source(출처)

[showcase]    성과 하이라이트
  필드: title(성과 제목), body(성과 요약 2~3문장),
        icon1·icon2·icon3 각각 "제목:서브" 형식 (예: "정확도:95.3% 달성")

[closing]     마무리
  필드: title_white(흰색 제목 텍스트), title_accent(강조색 제목 텍스트),
        body(마무리 메시지 2~3문장)

[brand]       기관 브랜딩 (마지막 카드로만 사용)
  필드: tagline(기관 슬로건 2줄), body(기관 소개 2~3문장),
        cta(연락처·URL), footer_text(기관명)
"""

# ---------------------------------------------------------------------------
# 템플릿 배치 규칙
# ---------------------------------------------------------------------------

_SEQUENCING_RULES = """
템플릿 배치 규칙:
- 첫 번째 카드는 반드시 [cover]
- 마지막 카드는 [closing] 또는 [brand] 중 하나
- 두 번째 카드는 [hook] 또는 [problem] 권장
- [data]는 수치가 3개 이상 비교 가능할 때만 사용
- [compare2]는 기존 vs 신기술 대비가 명확할 때만 사용
- [circle3]은 독립적인 3요소가 존재할 때 사용
- [brand]는 기관 홍보 목적일 때 closing 대신 사용
- 카드 간 내용 중복 최소화
- 내러티브 흐름: 문제 제기 → 기술 설명 → 성과 → 마무리
"""

# ---------------------------------------------------------------------------
# 프롬프트
# ---------------------------------------------------------------------------

_SYSTEM = """당신은 학술 논문을 기관 홍보용 카드뉴스로 변환하는 전문가입니다.
당신의 역할: 전체 스토리를 기획하고 디자인 결정(템플릿 선택)을 내린다.
사용자는 결과를 검토하고 수정할 권한을 가진다.

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


_MOCK_TEMPLATES = [
    "cover", "hook", "problem", "circle3", "compare2",
    "grid4", "definition", "flow", "data", "showcase", "closing", "brand",
]

_MOCK_FIELDS: dict[str, dict[str, FieldValue]] = {
    "cover": {
        "title":    _make_fv("탄소나노튜브 기반 고감도 가스 센서 개발"),
        "subtitle": _make_fv("0.1 ms 응답속도 · 95.3% 정확도 달성", section="results", page=2,
                             risk="CRITICAL", quality="exact", claim="quantitative"),
        "edition":  _make_fv("KITECH 연구성과 카드뉴스 2024-01호"),
    },
    "hook": {
        "title":         _make_fv("기존 가스센서, 왜 느리고 부정확한가?", section="introduction", page=1),
        "highlight":     _make_fv("CNT · 전기화학 · CVD", section="methods", page=2),
        "body":          _make_fv(
            "기존 금속산화물 센서는 응답속도가 0.25 ms 이상, 정확도 60% 수준에 그쳤다. "
            "실시간 공기질 모니터링·산업 안전 분야에서 한계가 명확했다.",
            section="introduction", page=1,
        ),
        "source_credit": _make_fv("Kim et al., KITECH 2024"),
    },
    "problem": {
        "title":    _make_fv("해결해야 할 과제", section="introduction", page=1),
        "body":     _make_fv(
            "기존 센서의 낮은 민감도와 느린 응답속도를 극복하기 위해 CVD 공법으로 "
            "성장시킨 CNT 어레이를 전극에 집적하는 새로운 접근법이 필요했다.",
            section="introduction", page=1,
        ),
        "emphasis": _make_fv("CVD 기반 CNT 어레이 전극 집적화"),
    },
    "circle3": {
        "title": _make_fv("핵심 3요소"),
        "body":  _make_fv("CNT 합성·전극 집적·전기화학 측정의 3단계 기술 융합"),
        "c1":    _make_fv("CVD 합성:핵심 공정:700°C 저압", section="methods", page=2),
        "c2":    _make_fv("전극 집적:나노 패터닝:1nm 선폭", section="methods", page=2),
        "c3":    _make_fv("전기화학:실시간 측정:실온 동작", section="methods", page=2),
    },
    "compare2": {
        "title":    _make_fv("기존 vs 신기술 비교"),
        "subtitle": _make_fv("응답속도 및 정확도 관점"),
        "label_a":  _make_fv("기존 금속산화물 센서"),
        "points_a": _make_fv("응답속도 0.25 ms·정확도 60%·고온 동작 필요", section="results", page=2,
                             risk="CRITICAL", quality="exact", claim="quantitative"),
        "label_b":  _make_fv("CNT 기반 신기술 (본 연구)"),
        "points_b": _make_fv("응답속도 0.1 ms·정확도 95.3%·실온 동작 가능", section="results", page=2,
                             risk="CRITICAL", quality="exact", claim="quantitative"),
    },
    "grid4": {
        "title":      _make_fv("기술 4대 특장점"),
        "subtitle":   _make_fv("CNT 센서 상용화 가능성 근거"),
        "item1_label": _make_fv("초고감도"),
        "item1_sub":   _make_fv("95.3% 정확도", section="results", page=2),
        "item2_label": _make_fv("초고속"),
        "item2_sub":   _make_fv("0.1 ms 응답속도", section="results", page=2),
        "item3_label": _make_fv("저전력"),
        "item3_sub":   _make_fv("실온 동작 가능", section="methods", page=2),
        "item4_label": _make_fv("내구성"),
        "item4_sub":   _make_fv("1,000회 이상 반복 측정 가능", section="results", page=2),
    },
    "definition": {
        "term":            _make_fv("CNT (탄소나노튜브)"),
        "term_detail":     _make_fv("Carbon Nanotube — 직경 1~10 nm 탄소 원자 구조체"),
        "definition_text": _make_fv(
            "탄소 원자가 육각형 격자를 이루며 말린 원통형 나노소재로 "
            "전기전도성·기계적 강도가 극히 뛰어나다.",
            section="methods", page=2,
        ),
        "body": _make_fv(
            "기체 분자 흡착 시 저항값이 즉각 변화해 고감도 가스 검출이 가능하다. "
            "기존 금속산화물 대비 응답속도 60% 향상, 정확도 35%p 개선이 가능하다.",
            section="results", page=2,
        ),
    },
    "flow": {
        "title":      _make_fv("제조 공정 흐름도", section="methods", page=2),
        "steps_text": _make_fv(
            "기판 세척·CVD 반응로 준비·CNT 합성 (700°C)·전극 패터닝·소자 조립·성능 평가",
            section="methods", page=2,
        ),
    },
    "data": {
        "title":    _make_fv("성능 비교 데이터", section="results", page=2),
        "data_unit": _make_fv("응답속도 (ms) / 정확도 (%)"),
        "bars":     _make_fv(
            "기존 센서 응답:0.25|CNT 센서 응답:0.10|기존 센서 정확도:60|CNT 센서 정확도:95",
            section="results", page=2, risk="CRITICAL", quality="exact", claim="quantitative",
        ),
        "bar_max":  _make_fv("95", section="results", page=2),
        "source":   _make_fv("Table 1. Kim et al., KITECH 2024"),
    },
    "showcase": {
        "title": _make_fv("연구 핵심 성과", section="results", page=2),
        "body":  _make_fv(
            "CNT 기반 가스 센서가 기존 대비 응답속도 60% 단축, 정확도 35%p 향상을 달성했다. "
            "실온 동작이 가능해 산업 현장 즉시 적용 가능성이 확인됐다.",
            section="results", page=2,
        ),
        "icon1": _make_fv("응답속도:0.1 ms 달성", section="results", page=2,
                          risk="CRITICAL", quality="exact", claim="quantitative"),
        "icon2": _make_fv("정확도:95.3% 달성", section="results", page=2,
                          risk="CRITICAL", quality="exact", claim="quantitative"),
        "icon3": _make_fv("개선율:기존 대비 40% 향상", section="results", page=2),
    },
    "closing": {
        "title_white":  _make_fv("탄소나노튜브로", section="conclusion", page=2),
        "title_accent": _make_fv("더 안전한 미래를", section="conclusion", page=2),
        "body": _make_fv(
            "고감도·고속 CNT 가스 센서 기술의 실용화 가능성이 확인됐다. "
            "산업 안전·환경 모니터링 분야에 즉시 적용 가능한 원천기술이다.",
            section="conclusion", page=2,
        ),
    },
    "brand": {
        "tagline":     _make_fv("기술로 만드는 더 나은 내일\n한국생산기술연구원"),
        "body":        _make_fv(
            "KITECH은 1989년 설립된 산업통상자원부 산하 연구기관으로 "
            "제조업 혁신을 위한 원천·응용 연구를 수행한다.",
        ),
        "cta":         _make_fv("www.kitech.re.kr"),
        "footer_text": _make_fv("한국생산기술연구원 (KITECH)"),
    },
}


def _build_mock_card_data(
    card_count: int,
    section_map: dict[str, str],
    paper_metadata,
) -> CardEditorData:
    """DEV_MOCK_LLM 모드용 — S1이 추출한 제목/저자 정보를 메타에 반영."""
    title = getattr(paper_metadata, "title", "") or "연구 성과"
    authors = getattr(paper_metadata, "authors", []) or []
    year = getattr(paper_metadata, "year", 2024) or 2024

    fv = _make_fv

    meta = CardMeta(
        org=fv("한국생산기술연구원"),
        dept=fv("나노소재연구부"),
        researcher=fv(authors[0] if authors else "연구팀"),
        month=fv(f"{year}-01", quality="normalized"),
        edition_number=fv(f"{year}-01호", quality="normalized"),
    )

    # card_count에 맞게 템플릿 시퀀스 슬라이싱
    sequence = _MOCK_TEMPLATES[:card_count]
    # 마지막은 항상 closing 또는 brand
    if sequence and sequence[-1] not in ("closing", "brand"):
        sequence[-1] = "closing"

    cards = [
        CardSlot(
            card_num=i + 1,
            template_type=tmpl,
            fields=_MOCK_FIELDS.get(tmpl, {"title": fv(title)}),
        )
        for i, tmpl in enumerate(sequence)
    ]

    _ROLE_MAP = {
        "cover": "논문 주제 소개",
        "hook": "문제 제기 및 독자 관심 유도",
        "problem": "기존 기술의 한계 제시",
        "circle3": "핵심 3요소 구조 설명",
        "compare2": "기존 vs 신기술 비교",
        "grid4": "4대 특장점 소개",
        "definition": "핵심 용어 정의",
        "flow": "연구 프로세스 시각화",
        "data": "정량 성과 수치 제시",
        "showcase": "핵심 성과 하이라이트",
        "closing": "마무리 및 의의",
        "brand": "기관 브랜딩",
    }
    storyboard = Storyboard(
        story_arc=f"{title}의 연구 배경·방법·성과를 {len(cards)}장으로 구성한 카드뉴스",
        beats=[
            CardStorybeat(
                card_num=i + 1,
                template_type=tmpl,
                narrative_role=_ROLE_MAP.get(tmpl, "내용 전달"),
                key_message=_MOCK_FIELDS.get(tmpl, {}).get(
                    "title", fv(title)
                ).value if _MOCK_FIELDS.get(tmpl) else title,
            )
            for i, tmpl in enumerate(sequence)
        ],
    )

    return CardEditorData(
        storyboard=storyboard, meta=meta, cards=cards,
        theme=THEME_PRESETS["tech_blue"],
        recommended_theme_key="tech_blue",
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
