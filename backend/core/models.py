from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal

import re

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# S6 Grounding primitives — do NOT change without updating docs/05_agent_design.md
# ---------------------------------------------------------------------------

class MatchQuality(str, Enum):
    EXACT = "exact"
    NORMALIZED = "normalized"
    FUZZY = "fuzzy"
    SEMANTIC = "semantic"
    FAILED = "failed"


class RiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ClaimType(str, Enum):
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    CAUSAL = "causal"


class DegradeCode(str, Enum):
    """파이프라인 단계별 degrade 사유. 코퍼스 하니스가 GROUP BY 하는 타입드 코드.
    StrEnum(3.11)은 못 쓰므로 (str, Enum). 야생 새 실패 모드 = 멤버 추가(린터가 전 참조 검증).
    유저향 warnings(문장)와 분리된 엔지니어링/측정 채널.
    설계: docs/superpowers/specs/2026-06-25-corpus-robustness-harness-design.md §4."""
    S1_NO_SECTIONS    = "s1_no_sections"
    S1_LOW_WORDS      = "s1_low_words"
    S1_EXTRACT_FAILED = "s1_extract_failed"
    S1_PARSE_FALLBACK = "s1_parse_fallback"
    S6_COVERAGE_MISMATCH = "s6_coverage_mismatch"
    S6_SCHEMA_INVALID    = "s6_schema_invalid"
    S6_TRUNCATED         = "s6_truncated"


class DegradeEvent(BaseModel):
    """degrade 한 건. layout=template_type(S6 카드-로컬일 때만), detail=사람용 부연(집계 X)."""
    code: DegradeCode
    layout: str | None = None
    detail: str = ""


# severity는 DegradeEvent 필드가 아니라 코드 분류(미니멀). hard = Mode B에서 short-circuit FAIL.
HARD_CODES: frozenset[DegradeCode] = frozenset({
    DegradeCode.S1_EXTRACT_FAILED,
    DegradeCode.S6_COVERAGE_MISMATCH,
    DegradeCode.S6_SCHEMA_INVALID,
    DegradeCode.S6_TRUNCATED,
})


class FieldSource(BaseModel):
    # section 기본값 "editor" = "원문 근거 없음" sentinel(FieldValue 기본 source와 동일 의미).
    # LLM이 못 찾은 필드를 source:{} / source 누락으로 내보내도 덱 전체가 죽지 않게 한다.
    # 실 호출 job f666b539: 논문에 없는 dept/month/edition_number를 모델이 source:{}로 보내
    # section 필수 검증이 깨지며 7장 전체가 ERR-S6-001로 사망 — 경계 강건화로 대응.
    # 주의: 수치 grounding은 match_quality로 risk를 매기므로(docs/06) 이 기본값이 정량 검증을
    # 약화시키지 않는다. 크래시(전체 손실)보다 degrade(sentinel)가 항상 낫다.
    section: str = "editor"
    page: int = 0

    @model_validator(mode="before")
    @classmethod
    def _coerce_source(cls, v: object) -> object:
        """LLM이 source를 비정형으로 내보낼 때(None / 문자열 / 빈 객체) dict로 정규화."""
        if v is None:
            return {}
        if isinstance(v, str):
            return {"section": v}
        return v

    @field_validator("page", mode="before")
    @classmethod
    def _coerce_page(cls, v: object) -> int:
        """LLM이 '1-2', '7, 1, 5' 등 복합 페이지를 문자열로 내보낼 때 첫 번째 정수만 취함."""
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            m = re.search(r"\d+", v)
            return int(m.group()) if m else 0
        return 0


class FieldValue(BaseModel):
    value: str = ""
    confidence: Literal["high", "medium", "low"] = "low"
    match_quality: MatchQuality = MatchQuality.SEMANTIC
    claim_type: ClaimType = ClaimType.QUALITATIVE
    source: FieldSource = Field(default_factory=lambda: FieldSource(section="editor", page=0))
    risk_level: RiskLevel = RiskLevel.LOW
    verified: bool = False

    @field_validator("match_quality", mode="before")
    @classmethod
    def _normalize_match_quality(cls, v: object) -> object:
        """LLM이 'mixed' 같은 enum 외 값을 반환할 때 FAILED로 안전 폴백."""
        if isinstance(v, str) and v not in {mq.value for mq in MatchQuality}:
            return MatchQuality.FAILED
        return v


class FieldStyle(BaseModel):
    """요소별 토큰-바운드 미세조정. 전 필드 선택적."""
    size: Literal["S", "M", "L", "XL"] | None = None
    tracking: float | None = None
    weight: Literal["regular", "bold"] | None = None
    align: Literal["left", "center", "right"] | None = None
    color: Literal["ink-strong", "ink-muted", "accent"] | None = None


# ---------------------------------------------------------------------------
# Card structure (v2 — variable card count)
# ---------------------------------------------------------------------------

IMAGE_MODES = {"box", "backdrop", "ghost", "none"}
VISUAL_KINDS = {"photo", "illustration"}

VALID_TEMPLATE_TYPES = {
    # 구 12 섬 템플릿 (섬 철거 슬라이스 전까지 공존)
    "cover", "hook", "problem", "circle3", "compare2",
    "grid4", "definition", "flow", "data", "showcase",
    "closing", "brand",
    # 신규 8 뼈대 (디자인 시스템)
    "cover_v2", "statement", "feature", "process_v2",
    "reasons", "grid_v2", "closing_v2", "bigstat_compare",
    # 확장 레이아웃 (6)
    "definition", "image_hero", "callout", "multistat", "quote", "compare_table",
    # 확장 레이아웃 (15~30) — docs/23_layout_catalog.md
    "radar_chart", "tradeoff_matrix", "terminal_block", "timeline", "checklist",
    "mythbuster", "growth_chart", "ab_split", "funnel", "datapath", "tech_grid",
    "decision_tree", "ticker", "do_dont", "swipe_bait", "chat",
}


class CardSlot(BaseModel):
    """단일 카드. template_type이 어떤 HTML 템플릿을 쓸지 결정."""
    card_num: int
    template_type: str                         # VALID_TEMPLATE_TYPES 중 하나
    fields: Dict[str, FieldValue]              # 템플릿 변수명 → grounded 값
    image_url: str | None = None               # 에디터 전용 이미지 슬롯
    focal: Dict[str, float] | None = None
    image_fit: str | None = None
    image_mode: str = "box"                    # 신규. 기본 'box' (하위 호환)
    visual_kind: str = "photo"                 # 에디터 전용(VISUAL_KINDS). S6/LLM은 설정 안 함
    field_styles: Dict[str, FieldStyle] | None = None   # 요소별 override(선택적)


class CardMeta(BaseModel):
    org: FieldValue
    dept: FieldValue
    researcher: FieldValue
    month: FieldValue
    edition_number: FieldValue


# ---------------------------------------------------------------------------
# Storyboard — S6가 콘텐츠 작성 전에 확정하는 전체 기획
# ---------------------------------------------------------------------------

class CardStorybeat(BaseModel):
    """카드 한 장의 기획 단위. template_type은 여기서 확정되고 CardSlot과 일치해야 한다."""
    card_num: int
    template_type: str
    narrative_role: str                        # 이 카드가 전체 스토리에서 하는 역할
    key_message: str                           # 이 카드에서 전달할 핵심 메시지 한 줄
    content_shape_reason: str = ""             # 설계팀이 이 뼈대를 고른 '내용 모양' 근거(선택)


class Storyboard(BaseModel):
    story_arc: str                             # 전체 스토리 한 문장 요약
    beats: List[CardStorybeat]


# ---------------------------------------------------------------------------
# Theme — defined here so CardEditorData can reference it
# ---------------------------------------------------------------------------

class CardTheme(BaseModel):
    primary: str = "#2563EB"
    dark: str = "#1A4C96"


THEME_PRESETS: dict[str, CardTheme] = {
    "tech_blue":     CardTheme(primary="#2563EB", dark="#1A4C96"),
    "forest_green":  CardTheme(primary="#16A34A", dark="#166534"),
    "sunset_orange": CardTheme(primary="#EA580C", dark="#9A3412"),
    "royal_violet":  CardTheme(primary="#7C3AED", dark="#4C1D95"),
    "golden_yellow": CardTheme(primary="#D97706", dark="#92400E"),
    "slate":         CardTheme(primary="#475569", dark="#1E293B"),
}


class CardEditorData(BaseModel):
    storyboard: Storyboard | None = None       # S6 기획 결과, 디버깅·UI 표시용
    meta: CardMeta
    cards: List[CardSlot]                      # 가변 길이 (S6가 결정)
    theme: CardTheme = Field(default_factory=CardTheme)
    recommended_theme_key: str | None = None
    bg_color: str | None = None                # 덱 배경 오버라이드(선택). None=세트 기본
    accent_color: str | None = None            # 덱 강조 오버라이드(선택). None=세트 기본
    font_pairing: str | None = None            # 덱 글꼴 오버라이드(선택). None=세트 기본(레지스트리 키)
    template_key: str | None = None            # 덱 비주얼 월드(템플릿) 선택(선택). None=기본(lab_note)


# ---------------------------------------------------------------------------
# Job / pipeline state
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    ERROR = "ERROR"


class RunState(BaseModel):
    job_id: str
    status: JobStatus
    stage: str | None = None
    progress: int = 0
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)
    title: str | None = None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# S1
# ---------------------------------------------------------------------------

class S1Input(BaseModel):
    job_id: str
    pdf_bytes: bytes


class PaperMetadata(BaseModel):
    title: str | None
    authors: list[str] = Field(default_factory=list)
    year: int | None
    doi: str | None


class S1Output(BaseModel):
    raw_text: str
    page_map: dict[int, str]
    section_map: dict[str, str] = Field(default_factory=dict)
    metadata: PaperMetadata
    word_count: int
    degraded: bool = False
    warnings: list[str] = Field(default_factory=list)
    degrade_events: list[DegradeEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# S6
# ---------------------------------------------------------------------------

class S6Input(BaseModel):
    job_id: str
    section_map: dict[str, str]
    page_map: dict[int, str]
    paper_metadata: PaperMetadata
    card_count: int = 5                        # 사용자가 요청한 카드 수


class S6Output(BaseModel):
    card_data: CardEditorData
    critical_count: int
    high_count: int
    warnings: list[str] = Field(default_factory=list)
    degrade_events: list[DegradeEvent] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# S6 내부 멀티에이전트 계약 (설계팀 Architect / 콘텐츠팀 Writer)
# S6Input/S6Output 은 동결 — 아래는 S6 코디네이터가 두 모듈을 중계할 때 쓰는 내부 타입.
# ---------------------------------------------------------------------------

class MismatchSignal(BaseModel):
    """Writer가 '이 뼈대엔 grounded 내용이 안 맞는다'고 설계팀에 되돌리는 신호."""
    card_num: int
    mismatch: bool = True
    reason: str
    suggested_shape: str = ""


class ArchitectInput(BaseModel):
    section_map: dict[str, str]
    paper_metadata: PaperMetadata
    card_count: int = 5
    revise_beats: list[MismatchSignal] | None = None     # 피드백 루프 2차: 지목 비트만 수정
    current_storyboard: Storyboard | None = None         # 2차 수정 시 기존 스토리보드 전달
    digest: "PaperDigest | None" = None                  # 있으면 digest 모드, 없으면 section_map(폴백)


class ArchitectOutput(BaseModel):
    storyboard: Storyboard
    recommended_theme: str


class WriterInput(BaseModel):
    section_map: dict[str, str]
    paper_metadata: PaperMetadata
    storyboard: Storyboard
    only_beats: list[int] | None = None                  # 부분 재작성 대상 card_num (없으면 전체)
    digest: "PaperDigest | None" = None                  # raw와 함께 힌트로


class WriterOutput(BaseModel):
    cards: list[CardSlot]
    meta: CardMeta
    mismatch_signals: list[MismatchSignal] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 논문이해팀 Understand — PaperDigest(내용모양 인벤토리). 다이제스트는 힌트, raw가 권위.
# ---------------------------------------------------------------------------

class DigestNumber(BaseModel):
    value: str                 # 숫자(가능하면 단위 제외)
    unit: str = ""
    label: str = ""            # 무엇을 재는 값인지
    context: str = ""          # 한 줄 의미
    source: FieldSource = Field(default_factory=lambda: FieldSource(section="", page=0))


class DigestComparison(BaseModel):
    attribute: str             # 비교 속성 (예: 압축강도)
    items: list[str] = Field(default_factory=list)    # 비교 대상명
    values: list[str] = Field(default_factory=list)   # 대상별 값(items와 병렬)
    source: FieldSource = Field(default_factory=lambda: FieldSource(section="", page=0))


class DigestTerm(BaseModel):
    term: str
    plain: str = ""            # 일상어 풀이


class DigestFigure(BaseModel):
    ref: str                   # 예: "Figure 3"
    shows: str = ""            # 한 줄 설명


class DigestClaim(BaseModel):
    role: str                  # problem|innovation|result|application|method
    text: str
    source: FieldSource = Field(default_factory=lambda: FieldSource(section="", page=0))


class PaperDigest(BaseModel):
    one_liner: str = ""
    numbers: list[DigestNumber] = Field(default_factory=list)
    comparisons: list[DigestComparison] = Field(default_factory=list)
    terms: list[DigestTerm] = Field(default_factory=list)
    figures: list[DigestFigure] = Field(default_factory=list)
    process_steps: list[str] = Field(default_factory=list)
    claims: list[DigestClaim] = Field(default_factory=list)
    domain_hint: str = ""


class UnderstandInput(BaseModel):
    section_map: dict[str, str]
    paper_metadata: PaperMetadata


# ---------------------------------------------------------------------------
# S7
# ---------------------------------------------------------------------------

class S7Input(BaseModel):
    job_id: str
    card_data: CardEditorData
    theme: CardTheme = Field(default_factory=CardTheme)


class S7Output(BaseModel):
    images: list[bytes]
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# S8
# ---------------------------------------------------------------------------

class S8Input(BaseModel):
    job_id: str
    card_data: CardEditorData
    images: list[bytes]
    warnings: list[str] = Field(default_factory=list)


class S8Output(BaseModel):
    job_id: str
    status: JobStatus


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------

class CardRenderStatus(str, Enum):
    PENDING = "PENDING"
    RENDERING = "RENDERING"
    DONE = "DONE"
    ERROR = "ERROR"


class ExportJob(BaseModel):
    export_job_id: str
    job_id: str
    cards: dict[int, CardRenderStatus]
    created_at: datetime
    zip_ready: bool = False
    error: str | None = None


# ArchitectInput/WriterInput 이 PaperDigest(아래에 정의)를 forward ref 로 참조 → 해소.
ArchitectInput.model_rebuild()
WriterInput.model_rebuild()
