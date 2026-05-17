from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, Literal

from pydantic import BaseModel, Field


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
    value: str
    confidence: Literal["high", "medium", "low"]
    match_quality: MatchQuality
    claim_type: ClaimType
    source: FieldSource
    risk_level: RiskLevel
    verified: bool = False


class CardMeta(BaseModel):
    org: FieldValue
    dept: FieldValue
    researcher: FieldValue
    month: FieldValue
    edition_number: FieldValue


class Card1(BaseModel):
    pretitle: FieldValue
    title: FieldValue
    mascot_bubble: FieldValue


class Card2Signals(BaseModel):
    is_hook: bool = False


class Card3Signals(BaseModel):
    stat_count: int = 0
    has_process_steps: bool = False
    step_count: int = 0


class Card4Signals(BaseModel):
    has_comparison: bool = False


class Card2(BaseModel):
    intro: FieldValue
    keyword_line: FieldValue
    footnote: FieldValue
    signals: Card2Signals = Field(default_factory=Card2Signals)


class Card3(BaseModel):
    problem: FieldValue
    achievement: FieldValue
    mascot_bubble: FieldValue
    photo_caption: FieldValue
    signals: Card3Signals = Field(default_factory=Card3Signals)


class Card4(BaseModel):
    before_label: FieldValue
    after_label: FieldValue
    description: FieldValue
    result: FieldValue
    mascot_bubble: FieldValue
    signals: Card4Signals = Field(default_factory=Card4Signals)


class Card5(BaseModel):
    pre_title: FieldValue
    main_title: FieldValue
    cta: FieldValue
    team_name: FieldValue


LayoutVariant = Literal["A", "B", "C", "D", "E", "G", "K"]


class CardEditorData(BaseModel):
    meta: CardMeta
    card1: Card1
    card2: Card2
    card3: Card3
    card4: Card4
    card5: Card5
    layout_variants: Dict[str, LayoutVariant] = Field(default_factory=dict)


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


class S6Input(BaseModel):
    job_id: str
    section_map: dict[str, str]
    page_map: dict[int, str]
    paper_metadata: PaperMetadata


class S6Output(BaseModel):
    card_data: CardEditorData
    critical_count: int
    high_count: int
    warnings: list[str] = Field(default_factory=list)


class CardTheme(BaseModel):
    primary: str = "#2563EB"
    dark: str = "#1A4C96"


class S7Input(BaseModel):
    job_id: str
    card_data: CardEditorData
    theme: CardTheme = Field(default_factory=CardTheme)


class S7Output(BaseModel):
    images: list[bytes]
    warnings: list[str] = Field(default_factory=list)


class S8Input(BaseModel):
    job_id: str
    card_data: CardEditorData
    images: list[bytes]
    warnings: list[str] = Field(default_factory=list)


class S8Output(BaseModel):
    job_id: str
    status: JobStatus


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
