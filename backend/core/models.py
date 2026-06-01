from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Literal

from pydantic import BaseModel, Field


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


class FieldSource(BaseModel):
    section: str
    page: int


class FieldValue(BaseModel):
    value: str = ""
    confidence: Literal["high", "medium", "low"] = "low"
    match_quality: MatchQuality = MatchQuality.SEMANTIC
    claim_type: ClaimType = ClaimType.QUALITATIVE
    source: FieldSource = Field(default_factory=lambda: FieldSource(section="editor", page=0))
    risk_level: RiskLevel = RiskLevel.LOW
    verified: bool = False


# ---------------------------------------------------------------------------
# Card structure (v2 — variable card count)
# ---------------------------------------------------------------------------

VALID_TEMPLATE_TYPES = {
    "cover", "hook", "problem", "circle3", "compare2",
    "grid4", "definition", "flow", "data", "showcase",
    "closing", "brand",
}


class CardSlot(BaseModel):
    """단일 카드. template_type이 어떤 HTML 템플릿을 쓸지 결정."""
    card_num: int
    template_type: str                         # VALID_TEMPLATE_TYPES 중 하나
    fields: Dict[str, FieldValue]              # 템플릿 변수명 → grounded 값
    image_url: str | None = None               # 에디터 전용 이미지 슬롯


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
