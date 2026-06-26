# 코퍼스 하니스 Mode A (무료 S1 견고성 측정) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 무주석 PDF 폴더(현재 85편)를 S1만 돌려 단계별 degrade 텔레메트리를 `input_profile`(조판·저널)로 교차집계하는 무료 배치 하니스를 만든다.

**Architecture:** (1) 타입드 degrade 텔레메트리를 `core/models.py`에 추가(=Mode B와 공유하는 계약), (2) S1이 degrade 분기마다 `DegradeEvent`를 emit, (3) `input_profile`(논문당 columns·journal_family 결정론 추출), (4) `corpus_harness.py`가 프로세스 격리 Pool로 폴더를 돌려 리포트. S6/유료 회귀는 별도 Plan 2.

**Tech Stack:** Python 3.10(=`(str, Enum)`, `StrEnum` 금지), Pydantic v2, pdfplumber/pymupdf4llm(기존), `multiprocessing.Pool(maxtasksperchild)`, pytest.

**상위 설계:** `docs/superpowers/specs/2026-06-25-corpus-robustness-harness-design.md` (§4 텔레메트리, §5 코퍼스, §6 Mode A, §3 OOM 안정장치, §12 터치포인트).

---

## File Structure

| 파일 | 책임 | 신규/수정 |
|---|---|---|
| `backend/core/models.py` | `DegradeCode`/`DegradeEvent`/`HARD_CODES` + S1Output·S6Output에 `degrade_events` | 수정 |
| `backend/agents/s1_extractor.py` | degrade 분기마다 `DegradeEvent` emit (`warnings`는 유저향 유지) | 수정 |
| `backend/scripts/input_profile.py` | 논문당 `{columns, journal_family}` 결정론 추출 | 신규 |
| `backend/scripts/corpus_harness.py` | Mode A CLI + Pool 배치 + 리포트 | 신규 |
| `backend/tests/test_degrade_telemetry.py` | 텔레메트리 타입 계약 | 신규 |
| `backend/tests/test_s1_degrade_events.py` | S1 emit | 신규 |
| `backend/tests/test_input_profile.py` | input_profile 결정론 | 신규 |
| `backend/tests/test_corpus_harness.py` | 워커·집계·리포트 | 신규 |
| `docs/05_agent_design.md`·`docs/07_api_data_model.md` | degrade_events 계약 | 수정 |
| `docs/04_architecture.md` | S2 흡수 드리프트 정정 | 수정 |

**테스트 실행 기준 명령**: `python -m pytest backend/tests -q` (이 프로젝트의 *살아있는* 스위트. `pytest.ini`가 가리키는 `tests/unit/`은 죽은 구 S6 테스트라 무시 — 메모리 `feedback_pytest_dead_suite`).

---

### Task 1: Degrade 텔레메트리 원시 타입 (models.py)

**Files:**
- Modify: `backend/core/models.py` (enum 블록 근처 + S1Output:221 + S6Output:243)
- Test: `backend/tests/test_degrade_telemetry.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# backend/tests/test_degrade_telemetry.py
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core.models import DegradeCode, DegradeEvent, HARD_CODES, S1Output, S6Output


def test_degradecode_is_str_enum_with_expected_members():
    # Python 3.10 — StrEnum(3.11) 금지, (str, Enum) 관용구. 값은 소문자 코드.
    assert DegradeCode.S1_NO_SECTIONS.value == "s1_no_sections"
    assert DegradeCode.S6_TRUNCATED.value == "s6_truncated"
    assert DegradeCode("s1_low_words") is DegradeCode.S1_LOW_WORDS  # str 비교 가능


def test_degrade_event_defaults():
    e = DegradeEvent(code=DegradeCode.S1_NO_SECTIONS)
    assert e.layout is None
    assert e.detail == ""
    e2 = DegradeEvent(code=DegradeCode.S6_SCHEMA_INVALID, layout="compare_table", detail="card 3")
    assert e2.layout == "compare_table"


def test_hard_codes_membership():
    # severity = 필드가 아니라 코드 분류(spec §4). hard 코드가 short-circuit FAIL 대상.
    assert DegradeCode.S6_TRUNCATED in HARD_CODES
    assert DegradeCode.S6_SCHEMA_INVALID in HARD_CODES
    assert DegradeCode.S6_COVERAGE_MISMATCH in HARD_CODES
    assert DegradeCode.S1_EXTRACT_FAILED in HARD_CODES
    assert DegradeCode.S1_NO_SECTIONS not in HARD_CODES   # soft


def test_outputs_have_degrade_events_default_empty():
    s1 = S1Output(raw_text="x", page_map={1: "x"}, metadata=_min_meta(), word_count=1)
    assert s1.degrade_events == []
    s6 = S6Output(card_data=_min_card_data())
    assert s6.degrade_events == []


def _min_meta():
    from backend.core.models import PaperMetadata
    return PaperMetadata(title=None, authors=[], year=None, doi=None)


def _min_card_data():
    from backend.core.models import CardEditorData, CardMeta, FieldValue
    fv = FieldValue(value="x")
    return CardEditorData(meta=CardMeta(org=fv, dept=fv, researcher=fv, month=fv, edition_number=fv), cards=[])
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest backend/tests/test_degrade_telemetry.py -q`
Expected: FAIL — `ImportError: cannot import name 'DegradeCode'`

- [ ] **Step 3: 최소 구현**

`backend/core/models.py`의 `class ClaimType(str, Enum):` 블록(31줄) 바로 뒤에 추가:

```python
class DegradeCode(str, Enum):
    """파이프라인 단계별 degrade 사유. 하니스가 GROUP BY 하는 타입드 코드.
    StrEnum(3.11)은 못 쓰므로 (str, Enum). 야생 새 실패 모드 = 멤버 추가(린터가 전 참조 검증)."""
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
```

`S1Output`(221줄)의 `warnings: list[str] = ...` 줄 바로 뒤에 추가:

```python
    degrade_events: list[DegradeEvent] = Field(default_factory=list)
```

`S6Output`(243줄)에도 동일하게 `degrade_events: list[DegradeEvent] = Field(default_factory=list)` 추가(Mode B가 채울 자리 — 지금은 빈 채로 계약만).

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest backend/tests/test_degrade_telemetry.py -q`
Expected: PASS (4 passed)

- [ ] **Step 5: 회귀 확인 + 커밋**

Run: `python -m pytest backend/tests -q`
Expected: 기존 127 + 4 = 131 passed

```bash
git add backend/core/models.py backend/tests/test_degrade_telemetry.py
git commit -m "[BE] degrade 텔레메트리 원시 타입 — DegradeCode/DegradeEvent/HARD_CODES + 출력 계약"
```

---

### Task 2: S1 degrade-event emission

**Files:**
- Modify: `backend/agents/s1_extractor.py` (`_clean_text` 위에 순수함수 추가 + `execute()` 반환부)
- Test: `backend/tests/test_s1_degrade_events.py`

순수 빌더 함수로 분리해 테스트 가능하게 한다(실 PDF 크래프팅 회피). `execute()`는 플래그만 계산해 빌더 호출.

- [ ] **Step 1: 실패 테스트 작성**

```python
# backend/tests/test_s1_degrade_events.py
from __future__ import annotations

import asyncio
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.agents.s1_extractor import build_s1_degrade_events, s1_agent
from backend.core.models import DegradeCode, S1Input


def _codes(events):
    return [e.code for e in events]


def test_builder_no_degrade_when_healthy():
    ev = build_s1_degrade_events(word_count=5000, min_word_count=100,
                                 section_degraded=False, parse_fallback=False)
    assert ev == []


def test_builder_low_words_carries_detail():
    ev = build_s1_degrade_events(word_count=40, min_word_count=100,
                                 section_degraded=False, parse_fallback=False)
    assert _codes(ev) == [DegradeCode.S1_LOW_WORDS]
    assert "40" in ev[0].detail


def test_builder_no_sections():
    ev = build_s1_degrade_events(word_count=5000, min_word_count=100,
                                 section_degraded=True, parse_fallback=False)
    assert _codes(ev) == [DegradeCode.S1_NO_SECTIONS]


def test_builder_parse_fallback_and_no_sections_both():
    ev = build_s1_degrade_events(word_count=5000, min_word_count=100,
                                 section_degraded=True, parse_fallback=True)
    assert set(_codes(ev)) == {DegradeCode.S1_PARSE_FALLBACK, DegradeCode.S1_NO_SECTIONS}


def test_execute_empty_bytes_emits_extract_failed():
    # 빈 입력 = 추출 불가 = EXTRACT_FAILED (하드 코드). 실 PDF 없이 검증 가능한 경로.
    out = asyncio.run(s1_agent.execute(S1Input(job_id="t", pdf_bytes=b"")))
    assert DegradeCode.S1_EXTRACT_FAILED in _codes(out.degrade_events)
    assert out.degraded is True
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest backend/tests/test_s1_degrade_events.py -q`
Expected: FAIL — `ImportError: cannot import name 'build_s1_degrade_events'`

- [ ] **Step 3: 최소 구현**

`backend/agents/s1_extractor.py` 상단 import에 추가:

```python
from ..core.models import DegradeCode, DegradeEvent
```

`_clean_text` 함수 정의 위에 순수 빌더 추가:

```python
def build_s1_degrade_events(
    *, word_count: int, min_word_count: int,
    section_degraded: bool, parse_fallback: bool,
) -> list[DegradeEvent]:
    """S1 degrade 사유를 타입드 이벤트로. EXTRACT_FAILED는 execute()의 빈입력/양쪽실패
    경로에서 직접 emit(여기 인자에 없음)."""
    events: list[DegradeEvent] = []
    if parse_fallback:
        events.append(DegradeEvent(code=DegradeCode.S1_PARSE_FALLBACK))
    if word_count < min_word_count:
        events.append(DegradeEvent(code=DegradeCode.S1_LOW_WORDS, detail=f"{word_count} words"))
    if section_degraded:
        events.append(DegradeEvent(code=DegradeCode.S1_NO_SECTIONS))
    return events
```

`execute()` 안의 **빈 입력 early-return**(`if not pdf_bytes:` 블록)의 `S1Output(...)`에 추가:

```python
                degrade_events=[DegradeEvent(code=DegradeCode.S1_EXTRACT_FAILED)],
```

`execute()` 안 **양쪽 추출 실패 early-return**(`if not page_map:` 블록)의 `S1Output(...)`에도 동일하게 추가:

```python
                degrade_events=[DegradeEvent(code=DegradeCode.S1_EXTRACT_FAILED)],
```

`execute()`에서 pymupdf4llm→pdfplumber 폴백 여부를 추적할 플래그를 추가한다. `warnings: list[str] = []` 선언 근처에:

```python
        parse_fallback = False
```

`except Exception as exc:` (pymupdf4llm 실패 → pdfplumber 폴백) 블록 안, `warnings.append(...)` 옆에:

```python
            parse_fallback = True
```

**메인 성공 경로의 최종 `return S1Output(...)`**(word_count·section_degraded 계산 뒤)에 추가:

```python
            degrade_events=build_s1_degrade_events(
                word_count=word_count, min_word_count=self._MIN_WORD_COUNT,
                section_degraded=section_degraded, parse_fallback=parse_fallback,
            ),
```

> 주의: `warnings`(유저향 문장)는 *그대로 둔다* — degrade_events는 별도 엔지니어링 채널(spec §4 SoC).

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest backend/tests/test_s1_degrade_events.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: 회귀 + 커밋**

Run: `python -m pytest backend/tests -q`
Expected: 131 + 5 = 136 passed

```bash
git add backend/agents/s1_extractor.py backend/tests/test_s1_degrade_events.py
git commit -m "[BE] S1 degrade-event emission — 순수 빌더 + execute 분기 (warnings 유지)"
```

---

### Task 3: input_profile — journal_family (DOI 접두사, 순수)

**Files:**
- Create: `backend/scripts/input_profile.py`
- Test: `backend/tests/test_input_profile.py`

- [ ] **Step 1: 실패 테스트 작성**

```python
# backend/tests/test_input_profile.py
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.scripts.input_profile import journal_family_from_doi


def test_known_publishers():
    assert journal_family_from_doi("10.1016/j.carbpol.2024.01") == "Elsevier"
    assert journal_family_from_doi("10.1002/anie.202012345") == "Wiley"
    assert journal_family_from_doi("10.1038/s41586-024-00001") == "Nature"


def test_none_or_garbage_is_unknown():
    assert journal_family_from_doi(None) == "unknown"
    assert journal_family_from_doi("") == "unknown"
    assert journal_family_from_doi("not-a-doi") == "unknown"


def test_unknown_prefix_keeps_prefix():
    assert journal_family_from_doi("10.9999/x.y").startswith("other:10.9999")
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest backend/tests/test_input_profile.py -q`
Expected: FAIL — `ModuleNotFoundError: backend.scripts.input_profile`

- [ ] **Step 3: 최소 구현**

```python
# backend/scripts/input_profile.py
"""논문당 입력 물성(input_profile) 결정론 추출 — Mode A 집계축(spec §4·§6).
S1 취약성은 카드 layout이 아니라 *입력 문서 물성*(조판·저널)으로 묶어야 핀셋 가치가 산다."""
from __future__ import annotations

import re

# DOI 등록기관 접두사 → 퍼블리셔. 있을 때만 — 없으면 unknown.
PUBLISHER_BY_DOI_PREFIX = {
    "10.1016": "Elsevier", "10.1002": "Wiley", "10.1021": "ACS",
    "10.1039": "RSC", "10.1038": "Nature", "10.1073": "PNAS",
    "10.1101": "bioRxiv", "10.48550": "arXiv", "10.1109": "IEEE",
    "10.1145": "ACM",
}


def journal_family_from_doi(doi: str | None) -> str:
    if not doi:
        return "unknown"
    m = re.match(r"(10\.\d{4,9})/", doi.strip())
    if not m:
        return "unknown"
    prefix = m.group(1)
    return PUBLISHER_BY_DOI_PREFIX.get(prefix, f"other:{prefix}")
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest backend/tests/test_input_profile.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/scripts/input_profile.py backend/tests/test_input_profile.py
git commit -m "[BE] input_profile — DOI 접두사 → journal_family (순수)"
```

---

### Task 4: input_profile — column 검출

**Files:**
- Modify: `backend/scripts/input_profile.py` (순수 결정함수 + pdfplumber 래퍼 + 통합 빌더)
- Test: `backend/tests/test_input_profile.py` (추가)

단어 중심좌표(정규화 0~1) 분포로 2단 판정: 좌/우 절반이 모두 차고 중앙 거터가 비면 2단. 순수 결정함수 `columns_from_centers`를 분리해 테스트.

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_input_profile.py` 끝에 추가:

```python
from backend.scripts.input_profile import columns_from_centers, build_input_profile


def test_columns_single_when_centered():
    centers = [0.5, 0.48, 0.52, 0.45, 0.55] * 20   # 모두 중앙 → 1단
    assert columns_from_centers(centers) == 1


def test_columns_two_when_bimodal_with_gutter():
    left = [0.2, 0.25, 0.3] * 20
    right = [0.7, 0.75, 0.8] * 20                   # 양쪽 차고 중앙 빔 → 2단
    assert columns_from_centers(left + right) == 2


def test_columns_one_when_empty():
    assert columns_from_centers([]) == 1


def test_build_input_profile_merges_columns_and_journal(monkeypatch):
    import backend.scripts.input_profile as ip
    monkeypatch.setattr(ip, "detect_columns", lambda pdf_bytes: 2)
    prof = ip.build_input_profile(b"%PDF-fake", "10.1016/j.x")
    assert prof == {"columns": 2, "journal_family": "Elsevier"}
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest backend/tests/test_input_profile.py -q`
Expected: FAIL — `ImportError: cannot import name 'columns_from_centers'`

- [ ] **Step 3: 최소 구현**

`backend/scripts/input_profile.py`에 추가:

```python
from io import BytesIO

import pdfplumber

# 거터(중앙 빈 띠) 판정 파라미터 — Golden/코퍼스로 후속 캘리브레이션 가능.
_GUTTER_LO, _GUTTER_HI = 0.42, 0.58
_SIDE_MIN = 0.25     # 좌·우 각 절반이 최소 이만큼 차야 2단 후보
_GUTTER_MAX = 0.10   # 중앙 거터가 이보다 비어야 2단


def columns_from_centers(centers: list[float]) -> int:
    """정규화 단어 중심좌표(0~1) 분포 → 1 또는 2단. 순수·결정론."""
    if not centers:
        return 1
    n = len(centers)
    left = sum(1 for c in centers if c < _GUTTER_LO) / n
    right = sum(1 for c in centers if c > _GUTTER_HI) / n
    central = sum(1 for c in centers if _GUTTER_LO <= c <= _GUTTER_HI) / n
    if left > _SIDE_MIN and right > _SIDE_MIN and central < _GUTTER_MAX:
        return 2
    return 1


def detect_columns(pdf_bytes: bytes) -> int:
    """앞 5페이지 단어 중심좌표를 모아 columns_from_centers에 위임. 파싱 실패 시 1."""
    centers: list[float] = []
    try:
        with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages[:5]:
                w = page.width or 1
                for word in page.extract_words():
                    centers.append(((word["x0"] + word["x1"]) / 2) / w)
    except Exception:
        return 1
    return columns_from_centers(centers)


def build_input_profile(pdf_bytes: bytes, doi: str | None) -> dict:
    """논문 1편 → {columns, journal_family}. Mode A가 GROUP BY 하는 메타."""
    return {
        "columns": detect_columns(pdf_bytes),
        "journal_family": journal_family_from_doi(doi),
    }
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest backend/tests/test_input_profile.py -q`
Expected: PASS (7 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/scripts/input_profile.py backend/tests/test_input_profile.py
git commit -m "[BE] input_profile — 단어 x좌표 군집 column 검출 + 통합 빌더"
```

---

### Task 5: corpus_harness — 단일 논문 워커

**Files:**
- Create: `backend/scripts/corpus_harness.py`
- Test: `backend/tests/test_corpus_harness.py`

워커 `profile_one(pdf_path)`은 S1 실행 + input_profile → 직렬화 가능한 dict 반환(Pool 전송 위해 dict). S1은 비동기라 `asyncio.run`.

- [ ] **Step 1: 실패 테스트 작성**

```python
# backend/tests/test_corpus_harness.py
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

import backend.scripts.corpus_harness as harness


def test_profile_one_returns_serializable_row(monkeypatch, tmp_path):
    # S1·input_profile을 가짜로 — 워커 오케스트레이션(파일읽기→실행→직렬화)만 검증.
    from backend.core.models import DegradeCode, DegradeEvent, PaperMetadata, S1Output

    fake_s1 = S1Output(
        raw_text="x", page_map={1: "x"},
        metadata=PaperMetadata(title=None, authors=[], year=None, doi="10.1016/j.x"),
        word_count=5000, degraded=True,
        degrade_events=[DegradeEvent(code=DegradeCode.S1_NO_SECTIONS)],
    )

    async def fake_execute(inp):
        return fake_s1

    monkeypatch.setattr(harness.s1_agent, "execute", fake_execute)
    monkeypatch.setattr(harness, "build_input_profile",
                        lambda pdf_bytes, doi: {"columns": 2, "journal_family": "Elsevier"})

    pdf = tmp_path / "paper_a.pdf"
    pdf.write_bytes(b"%PDF-fake")
    row = harness.profile_one(str(pdf))

    assert row == {
        "file": "paper_a.pdf",
        "codes": ["s1_no_sections"],
        "columns": 2,
        "journal_family": "Elsevier",
    }
    # 직렬화 가능(enum 아님 — Pool 전송 안전)
    import json
    json.dumps(row)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest backend/tests/test_corpus_harness.py -q`
Expected: FAIL — `ModuleNotFoundError: backend.scripts.corpus_harness`

- [ ] **Step 3: 최소 구현**

```python
# backend/scripts/corpus_harness.py
"""코퍼스 견고성 하니스 — Mode A(무료 S1 측정).
폴더의 모든 PDF를 S1만 돌려 degrade 텔레메트리를 input_profile로 교차집계한다.
프로세스 격리 Pool(maxtasksperchild)로 fitz C-메모리 OOM 회피(spec §3).
오프라인 개발 도구 — 웹/프로덕션과 무관."""
from __future__ import annotations

import asyncio
from pathlib import Path

from backend.agents.s1_extractor import s1_agent
from backend.core.models import S1Input
from backend.scripts.input_profile import build_input_profile


def profile_one(pdf_path: str) -> dict:
    """논문 1편 → 직렬화 가능 row(Pool 전송 위해 enum 아닌 str). 워커 진입점."""
    pdf_bytes = Path(pdf_path).read_bytes()
    s1 = asyncio.run(s1_agent.execute(S1Input(job_id=pdf_path, pdf_bytes=pdf_bytes)))
    profile = build_input_profile(pdf_bytes, s1.metadata.doi)
    return {
        "file": Path(pdf_path).name,
        "codes": [e.code.value for e in s1.degrade_events],
        "columns": profile["columns"],
        "journal_family": profile["journal_family"],
    }
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest backend/tests/test_corpus_harness.py -q`
Expected: PASS (1 passed)

- [ ] **Step 5: 커밋**

```bash
git add backend/scripts/corpus_harness.py backend/tests/test_corpus_harness.py
git commit -m "[BE] corpus_harness — 단일 논문 워커(S1+input_profile, 직렬화 row)"
```

---

### Task 6: corpus_harness — Pool 배치 + 리포트 + CLI

**Files:**
- Modify: `backend/scripts/corpus_harness.py` (배치·집계·리포트·main)
- Test: `backend/tests/test_corpus_harness.py` (추가)

집계·리포트는 순수 함수(`aggregate`, `format_report`)로 분리해 테스트. 실제 배치(`run_mode_a`)는 Pool을 쓰고 CLI(`main`)에서만 호출(테스트는 순수부만).

- [ ] **Step 1: 실패 테스트 추가**

`backend/tests/test_corpus_harness.py` 끝에 추가:

```python
def test_aggregate_counts_codes_and_crosstab():
    rows = [
        {"file": "a.pdf", "codes": ["s1_no_sections"], "columns": 2, "journal_family": "Elsevier"},
        {"file": "b.pdf", "codes": ["s1_no_sections"], "columns": 2, "journal_family": "Elsevier"},
        {"file": "c.pdf", "codes": [], "columns": 1, "journal_family": "arXiv"},
    ]
    agg = harness.aggregate(rows)
    assert agg["total"] == 3
    assert agg["clean"] == 1
    assert agg["by_code"]["s1_no_sections"] == 2
    # 교차표: NO_SECTIONS가 (columns=2, Elsevier)에 2건
    assert agg["crosstab"]["s1_no_sections"][("2", "Elsevier")] == 2


def test_format_report_is_nonempty_text():
    rows = [{"file": "a.pdf", "codes": ["s1_no_sections"], "columns": 2, "journal_family": "Elsevier"}]
    report = harness.format_report(harness.aggregate(rows))
    assert "s1_no_sections" in report
    assert "Elsevier" in report
    assert "a.pdf" in report
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest backend/tests/test_corpus_harness.py -q`
Expected: FAIL — `AttributeError: module ... has no attribute 'aggregate'`

- [ ] **Step 3: 최소 구현**

`backend/scripts/corpus_harness.py`에 추가:

```python
import argparse
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool

_PDF_GLOB = "*.pdf"


def aggregate(rows: list[dict]) -> dict:
    """rows → code별 카운트 + (degrade code × input_profile) 교차표."""
    by_code: Counter = Counter()
    crosstab: dict[str, Counter] = defaultdict(Counter)
    files_by_code: dict[str, list[str]] = defaultdict(list)
    clean = 0
    for r in rows:
        if not r["codes"]:
            clean += 1
        for code in r["codes"]:
            by_code[code] += 1
            crosstab[code][(str(r["columns"]), r["journal_family"])] += 1
            files_by_code[code].append(r["file"])
    return {
        "total": len(rows),
        "clean": clean,
        "by_code": dict(by_code),
        "crosstab": {k: dict(v) for k, v in crosstab.items()},
        "files_by_code": dict(files_by_code),
    }


def format_report(agg: dict) -> str:
    lines = [f"=== S1 견고성 리포트 ({agg['total']}편) ==="]
    parts = [f"{c} {n}" for c, n in sorted(agg["by_code"].items())]
    lines.append("code별: " + " / ".join(parts) + f" / 정상 {agg['clean']}")
    for code, cells in agg["crosstab"].items():
        lines.append(f"\n{code} × input_profile (← 핀셋 대상):")
        for (cols, journal), n in sorted(cells.items(), key=lambda kv: -kv[1]):
            lines.append(f"  columns={cols} · journal={journal} : {n}편")
        sample = agg["files_by_code"][code][:5]
        lines.append("  예: " + ", ".join(sample))
    return "\n".join(lines)


def run_mode_a(corpus_dir: str, workers: int = 4, maxtasks: int = 10) -> list[dict]:
    """폴더의 모든 PDF를 프로세스 격리 Pool로 S1 측정. maxtasksperchild로 fitz OOM 회피."""
    paths = [str(p) for p in sorted(Path(corpus_dir).glob(_PDF_GLOB))]
    if not paths:
        return []
    with Pool(processes=workers, maxtasksperchild=maxtasks) as pool:
        return pool.map(profile_one, paths)


def main() -> None:
    ap = argparse.ArgumentParser(description="코퍼스 견고성 하니스")
    ap.add_argument("--stage", choices=["s1"], default="s1",
                    help="s1=무료 whack-a-mole(Mode A). full(Mode B)은 Plan 2.")
    ap.add_argument("--corpus", required=True, help="PDF 폴더 경로")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    if args.stage != "s1":
        print("Mode B(full)는 유료 — Plan 2에서 구현. 지금은 --stage s1만.", file=sys.stderr)
        sys.exit(2)

    rows = run_mode_a(args.corpus, workers=args.workers)
    print(format_report(aggregate(rows)))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest backend/tests/test_corpus_harness.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: 실제 코퍼스 스모크(무료 — 비용 없음, 박사님 폴더)**

Run:
```bash
python -m backend.scripts.corpus_harness --stage s1 \
  --corpus "C:/Users/User/Desktop/한국생산기술연구원_근로장학/poly_claude_code/논문"
```
Expected: `=== S1 견고성 리포트 (85편) ===` 헤더 + code별 줄 + 교차표 출력(에러 없이 완주 = OOM 안정장치 동작). **LLM 호출 0 → 비용 0.**

- [ ] **Step 6: 회귀 + 커밋**

Run: `python -m pytest backend/tests -q`
Expected: 136 + 3 = 139 passed

```bash
git add backend/scripts/corpus_harness.py backend/tests/test_corpus_harness.py
git commit -m "[BE] corpus_harness Mode A — Pool 배치(OOM격리)+교차표 리포트+CLI"
```

---

### Task 7: docs 계약·드리프트 반영 (docs-before-code 사후 정합)

**Files:**
- Modify: `docs/07_api_data_model.md` (S1Output/S6Output에 degrade_events)
- Modify: `docs/05_agent_design.md` (degrade_events 채널 = 엔지니어링, warnings = 유저향)
- Modify: `docs/04_architecture.md` (S2 흡수 드리프트 1줄 정정)

> CLAUDE.md는 docs-before-code지만, 이번엔 spec(2026-06-25)이 이미 계약을 정의·승인했으므로
> 여기서 canonical docs에 반영(동기화)한다.

- [ ] **Step 1: docs/07 — S1Output/S6Output 계약에 degrade_events 추가**

`docs/07_api_data_model.md`에서 S1Output(또는 파이프라인 출력) 명세 근처에 추가:

```
degrade_events: DegradeEvent[]   // 엔지니어링 텔레메트리(하니스 집계축). warnings(유저향)와 분리.
                                 // DegradeEvent = { code: DegradeCode, layout?: string, detail?: string }
                                 // DegradeCode: s1_no_sections | s1_low_words | s1_extract_failed |
                                 //   s1_parse_fallback | s6_coverage_mismatch | s6_schema_invalid | s6_truncated
```

- [ ] **Step 2: docs/05 — 채널 분리 명문화**

`docs/05_agent_design.md`의 §5-2 "파싱 강건성" 노트(2026-06-25에 추가한 곳) 뒤에 1단락 추가:

```
**degrade 텔레메트리(2026-06-25)**: 각 단계 출력의 `degrade_events: list[DegradeEvent]`는
*엔지니어링/측정* 채널이다(타입드 `DegradeCode`). 유저향 `warnings`(문장)와 분리 — 코퍼스
하니스가 `degrade_events[].code`를 GROUP BY 해 야생 취약성을 집계한다. severity는 필드가
아니라 코드 분류(`HARD_CODES`). 설계: specs/2026-06-25-corpus-robustness-harness-design.md.
```

- [ ] **Step 3: docs/04 — S2 드리프트 정정**

`docs/04_architecture.md`에서 파이프라인 단계를 "S1 → S2 → S6"로 적은 곳을 찾아 1줄 주석 추가
(실제 코드는 S2가 S1의 `_parse_sections`에 흡수, 오케스트레이터는 S1→S6 직행):

```
> 주의(2026-06-25 정정): 실제 파이프라인은 S1→S6→S7→S8. 섹션파싱(구 S2)은 S1의
> _parse_sections에 흡수돼 별도 단계가 아니다.
```

- [ ] **Step 4: 커밋**

```bash
git add docs/07_api_data_model.md docs/05_agent_design.md docs/04_architecture.md
git commit -m "[DOCS] degrade_events 계약 반영 + S2 흡수 드리프트 정정"
```

---

## Self-Review (작성자 체크 — 완료)

**Spec 커버리지**: §4 텔레메트리→Task 1, §4 S1 emit→Task 2, §4 input_profile→Task 3·4,
§6 Mode A 리포트→Task 6, §3 OOM Pool→Task 6, §12 docs→Task 7. **Mode B 관련(§7 invariants,
Golden expectations, S6 emit)은 의도적으로 Plan 2로 분리** — 이 Plan은 무료 Mode A만으로 완결.

**Placeholder 스캔**: 없음. 모든 스텝에 실제 코드·명령·기대출력.

**타입 일관성**: `DegradeCode`/`DegradeEvent`/`HARD_CODES`(Task 1) → `build_s1_degrade_events`(Task 2) →
`journal_family_from_doi`/`columns_from_centers`/`build_input_profile`(Task 3·4) →
`profile_one`/`aggregate`/`format_report`/`run_mode_a`(Task 5·6). 이름·시그니처 전 태스크 일치 확인.
`code.value`(str) 직렬화로 Pool 전송 안전(enum 직렬화 함정 회피).

**알려진 후속(Plan 2)**: S6 degrade emit(layout 태깅), invariants.py(4층+HARD_CODES short-circuit+
char-shingle Jaccard), golden/expectations.yaml, Mode B CLI(--stage full, 유료·사전허락).
