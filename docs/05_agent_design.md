# 05 · Agent Design
> PolyInsight v2.0 | 2026-05-11
> 에이전트 계약(Agent Contracts) 및 S6 프롬프트 규칙
> CLAUDE.md §3·§4·§5·§6을 코드 수준으로 구체화한 문서.

---

## 1. 개요

### 1-1. 설계 원칙

```
1. Orchestrator가 에이전트의 유일한 호출자다.
   에이전트는 다른 에이전트를 직접 호출하지 않는다.

2. 각 에이전트는 정의된 InputT를 받고 OutputT를 반환한다.
   중간 상태를 외부에 노출하지 않는다.

3. 에이전트는 RunState를 직접 수정하지 않는다.
   Orchestrator가 OutputT를 받아 RunState를 갱신한다.

4. 실패는 예외(exception)가 아닌 반환값(OutputT의 warnings/degraded)으로 표현한다.
   단, S1 블로킹 실패는 예외 허용 (Orchestrator가 catch).

5. S6는 section_map(원문)만을 사실 근거로 삼는다.
   LLM이 생성한 요약이나 외부 지식은 grounding 출처가 될 수 없다.
```

### 1-2. BaseAgent 인터페이스

```python
# backend/agents/base.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")

class BaseAgent(ABC, Generic[InputT, OutputT]):
    @abstractmethod
    async def execute(self, input_data: InputT) -> OutputT:
        raise NotImplementedError
```

모든 에이전트는 `BaseAgent[InputT, OutputT]`를 상속하고 `execute()`만 구현한다.
Orchestrator는 `await agent.execute(input_data)` 형태로만 호출한다.

---

## 2. Orchestrator 호출 순서

```python
# backend/orchestrator.py
async def run_pipeline(job_id: str, pdf_bytes: bytes) -> None:
    state = await db.create_job(job_id)

    # S1 — 블로킹 실패 허용
    try:
        s1_out: S1Output = await s1_agent.execute(S1Input(job_id=job_id, pdf_bytes=pdf_bytes))
    except Exception as e:
        await db.update_job(job_id, status=ERROR, warnings=[str(e)])
        await s8_agent.execute(S8Input(job_id=job_id, ...))  # 상태 기록
        return
    await db.update_job(job_id, stage="S2", progress=20)

    # S2
    s2_out: S2Output = await s2_agent.execute(S2Input(
        job_id=job_id,
        raw_text=s1_out.raw_text,
        page_map=s1_out.page_map,
    ))
    if s2_out.degraded_mode:
        state.degraded = True
        state.warnings += s2_out.warnings
    await db.update_job(job_id, stage="S6", progress=40, degraded=state.degraded)

    # S6
    s6_out: S6Output = await s6_agent.execute(S6Input(
        job_id=job_id,
        section_map=s2_out.section_map,
        page_map=s1_out.page_map,
        paper_metadata=s1_out.metadata,
    ))
    await db.save_card_data(job_id, s6_out.card_data)
    await db.update_job(job_id, stage="S7", progress=65)

    # S7
    s7_out: S7Output = await s7_agent.execute(S7Input(
        job_id=job_id,
        card_data=s6_out.card_data,
    ))
    await db.update_job(job_id, stage="S8", progress=90)

    # S8 — 항상 실행
    await s8_agent.execute(S8Input(
        job_id=job_id,
        card_data=s6_out.card_data,
        images=s7_out.images,
        warnings=state.warnings + s6_out.warnings + s7_out.warnings,
    ))
```

---

## 3. S1 — Text Extractor

**파일**: `backend/agents/s1_extractor.py`

### 3-1. 계약

| 항목 | 내용 |
|------|------|
| 입력 | `S1Input(job_id, pdf_bytes)` |
| 출력 | `S1Output(raw_text, page_map, metadata, word_count, warnings)` |
| 실패 유형 | **블로킹** — pdfplumber + PyMuPDF 모두 실패 시 예외 raise |
| 의존성 | `pdfplumber`, `PyMuPDF (fitz)` |

### 3-2. 처리 흐름

```
1. pdfplumber로 텍스트 추출 시도
   - 성공 → raw_text, page_map 구성
   - 실패 또는 텍스트 비율 < 10% (스캔본 의심) → PyMuPDF 폴백

2. PyMuPDF 폴백
   - 성공 → raw_text, page_map 구성, warnings에 "fallback to PyMuPDF" 추가
   - 실패 → ERR-S1-001 예외 raise

3. 메타데이터 추출 (best-effort)
   - PDF 속성(pdfplumber metadata) → title, authors, year, doi
   - 추출 실패해도 None 허용 (블로킹 아님)

4. word_count 계산 후 반환
```

### 3-3. 구현 제약

- 텍스트 추출 후 `word_count < 100`이면 warnings에 추가 (내용이 거의 없는 PDF)
- `page_map: dict[int, str]` — 키는 1-indexed 페이지 번호, 값은 해당 페이지 텍스트
- raw_text는 페이지 구분 없이 전체 연결 텍스트 (`"\n\n".join(page_map.values())`)
- 최대 파일 크기 50MB는 FastAPI 라우터에서 검증 (이 에이전트가 처리하지 않음)

---

## 4. S2 — Section Parser

**파일**: `backend/agents/s2_parser.py`

### 4-1. 계약

| 항목 | 내용 |
|------|------|
| 입력 | `S2Input(job_id, raw_text, page_map)` |
| 출력 | `S2Output(section_map, degraded_mode, warnings)` |
| 실패 유형 | **논블로킹** — 완전 실패 시 `degraded_mode=True`, 빈 section_map 반환 |
| 의존성 | regex, `llm_client` (LLM 폴백) |

### 4-2. 처리 흐름

```
1. Regex 기반 섹션 헤더 탐지
   패턴: r"^(Abstract|Introduction|Methods?|Results?|Discussion|
              Conclusion|References|Background|Related Work)[\s\n:]*"
   (대소문자 무관, 한국어 논문: 초록|방법론|결과|결론 등 추가 패턴)

2. 추출된 섹션 수 ≥ 3 → regex 성공, section_map 반환

3. 추출된 섹션 수 < 3 → LLM 폴백
   프롬프트: "다음 논문 텍스트를 Abstract, Introduction, Methods,
              Results, Discussion, Conclusion 섹션으로 분리하시오.
              각 섹션 이름과 내용을 JSON으로 반환하시오."
   LLM 응답 파싱 성공 → section_map 반환, warnings에 "LLM fallback used" 추가

4. LLM 폴백도 실패 → degraded_mode=True
   section_map = {"full_text": raw_text}  (전체를 단일 섹션으로)
   warnings에 "ERR-S2-001: section parsing failed, using full text" 추가
```

### 4-3. Degraded Mode 주의

- `degraded_mode=True`는 S6에 전달된다
- S6는 degraded_mode 상태에서도 실행되지만, 모든 FieldValue의 `confidence`를 `"low"`로 강제하고 `source.section`을 `"full_text"`로 기록해야 한다
- Degraded mode에서 생성된 카드는 절대 `confidence="high"`를 가질 수 없다

---

## 5. S6 — Card News JSON

**파일**: `backend/agents/s6_card_json.py`

S6는 파이프라인에서 **할루시네이션 위험이 가장 높은 단계**다.
이 섹션의 모든 규칙은 CLAUDE.md §3과 동일하며, 코드 구현 수준의 세부 명세를 추가한다.

### 5-1. 계약

| 항목 | 내용 |
|------|------|
| 입력 | `S6Input(job_id, section_map, page_map, paper_metadata)` |
| 출력 | `S6Output(card_data, critical_count, high_count, warnings)` |
| 실패 유형 | **논블로킹** — LLM 파싱 실패 3회 시 ERR-S6-001 (에이전트가 예외 raise하고 Orchestrator가 처리) |
| 의존성 | `llm_client` (Claude API), `FieldValue` 스키마 |

### 5-2. 그라운딩 규칙 (비협상)

```
RULE 1: section_map이 유일한 사실 출처다.
        LLM의 파라메트릭 지식(훈련 데이터)을 사실 근거로 쓰지 않는다.

RULE 2: 수치(숫자, %, 배율, 시간, 크기)를 포함하는 모든 FieldValue는
        source.section과 source.page를 반드시 채워야 한다.
        원문에서 해당 수치를 찾을 수 없으면 value에 수치를 넣지 않는다.

RULE 3: match_quality 판정 기준:
        - "exact"     : 원문에서 동일한 문자열을 찾을 수 있음
        - "normalized": 단위 변환, 줄임말 등 표준화 후 일치
        - "fuzzy"     : 의미는 동일하나 표현이 다름
        - "semantic"  : 직접 언급 없으나 문맥에서 추론 가능
        - "failed"    : 원문에서 근거를 찾을 수 없음

RULE 4: claim_type 판정 기준:
        - "quantitative": 수치/측정값 포함
        - "qualitative" : 수치 없는 서술적 주장
        - "causal"      : 인과관계 주장 ("A 때문에 B", "A를 통해 B")

RULE 5: risk_level 자동 판정:
        if claim_type == "quantitative" and match_quality == "failed":
            risk_level = "CRITICAL"
        elif match_quality in ("fuzzy", "semantic"):
            risk_level = "HIGH"
        elif match_quality == "normalized":
            risk_level = "MEDIUM"
        else:  # exact, qualitative
            risk_level = "LOW"

RULE 6: 원문에 없는 내용을 value로 생성하지 않는다.
        값을 만들 수 없으면 value = "" (빈 문자열), confidence = "low",
        match_quality = "failed", risk_level = "CRITICAL".

RULE 7: verified는 항상 False로 초기화한다. 사용자가 에디터에서만 True로 변경한다.
```

### 5-3. 처리 흐름 (Chain-of-Thought)

S6는 단일 LLM 호출이 아닌 **내부 3단계 chain-of-thought**를 거친다.
단, 외부로는 최종 `CardEditorData` JSON만 노출한다.

```
Step 1 — 논문 이해
  입력: section_map 전체 텍스트
  내부 질문:
    - 이 논문의 핵심 기술/기여는 무엇인가?
    - 정량적 성과 수치는 어디에 있는가? (섹션, 페이지 기록)
    - 기존 한계(problem)와 새 접근(achievement)은 무엇인가?
    - 연구팀/기관 정보는 어디에 있는가?
  출력: 내부 메모 (LLM context 내부에서만 사용)

Step 2 — 필드 매핑
  내부 질문:
    - CardEditorData의 각 필드에 무엇을 넣어야 하는가?
    - 각 값의 원문 근거 섹션과 페이지는?
    - match_quality와 confidence는 어떻게 판정해야 하는가?
  출력: 필드별 (value, source, match_quality, claim_type) 초안

Step 3 — FieldValue 생성 및 risk_level 판정
  RULE 5에 따라 risk_level 자동 판정
  최종 JSON 직렬화 및 Pydantic 검증
  출력: CardEditorData (JSON)
```

### 5-4. 시스템 프롬프트

```python
SYSTEM_PROMPT = """
당신은 학술 논문을 기관 홍보용 카드뉴스로 변환하는 전문가입니다.
당신의 역할은 다음과 같습니다:
1. 제공된 논문 원문(section_map)에서 정보를 추출한다.
2. 추출한 정보를 정해진 JSON 스키마(CardEditorData)로 변환한다.
3. 모든 값은 원문에서 직접 찾을 수 있는 내용만 사용한다.
4. 원문에 없는 내용은 절대 만들어내지 않는다.

핵심 원칙:
- 사실은 오직 아래 section_map에서만 온다.
- 수치(숫자, %, 배율)는 반드시 원문에서 찾아야 한다.
- 찾을 수 없으면 value=""로 남기고 match_quality="failed"로 표기한다.
- verified는 항상 false다.
"""

USER_PROMPT_TEMPLATE = """
## 논문 원문 (section_map)

{section_map_text}

---

## 논문 메타데이터

제목: {title}
저자: {authors}
연도: {year}
DOI: {doi}

---

## 요청

위 논문 원문을 분석하여 아래 JSON 스키마를 채우시오.

### 작업 순서

**Step 1 — 논문 핵심 파악 (내부 분석, 출력 불필요)**

다음을 원문에서 확인하라:
- 핵심 기술/기여 (한 문장)
- 정량적 성과 수치 (모든 숫자, %, 배율) + 각각의 섹션명과 페이지
- 기존 문제(problem) + 새 해결책(achievement)
- 연구팀/기관명, 연구 부서

**Step 2 — 필드별 원문 근거 확인**

아래 각 필드에 대해:
1. 원문에서 해당 내용을 찾는다
2. 찾으면 → match_quality를 exact/normalized/fuzzy/semantic 중 선택
3. 찾지 못하면 → value="", match_quality="failed"

**Step 3 — JSON 출력**

다음 스키마를 완성하여 JSON만 반환하라. 설명이나 마크다운 없이 JSON만.

{{
  "meta": {{
    "org": <FieldValue>,           // 기관명 (예: "한국생산기술연구원")
    "dept": <FieldValue>,          // 연구 부서/팀명
    "researcher": <FieldValue>,    // 대표 연구자 이름
    "month": <FieldValue>,         // 발표/게재 연월 (예: "2025년 3월")
    "edition_number": <FieldValue> // 카드뉴스 회차 또는 논문 식별자
  }},
  "card1": {{
    "pretitle": <FieldValue>,      // 카드1 상단 소제목 (예: "연구 분야 소개")
    "title": <FieldValue>,         // 카드1 메인 타이틀 (핵심 기술명, 20자 이내)
    "mascot_bubble": <FieldValue>  // 마스코트 말풍선 (흥미 유발, 1문장)
  }},
  "card2": {{
    "intro": <FieldValue>,         // 문제 제기 또는 배경 (2~3문장)
    "keyword_line": <FieldValue>,  // 핵심 키워드 나열 (예: "#스마트팜 #정식로봇")
    "footnote": <FieldValue>       // 출처 또는 보충 각주
  }},
  "card3": {{
    "problem": <FieldValue>,       // 기존 기술의 한계 (2~3문장)
    "achievement": <FieldValue>,   // 이 연구의 성과 (수치 포함 권장)
    "mascot_bubble": <FieldValue>, // 마스코트 말풍선
    "photo_caption": <FieldValue>  // 연구 사진 캡션 (없으면 "")
  }},
  "card4": {{
    "before_label": <FieldValue>,  // 비교 왼쪽 레이블 (예: "기존 방식")
    "after_label": <FieldValue>,   // 비교 오른쪽 레이블 (예: "신기술")
    "description": <FieldValue>,   // 비교 설명 (2~3문장)
    "result": <FieldValue>,        // 결과 수치 또는 효과 (수치 강조)
    "mascot_bubble": <FieldValue>  // 마스코트 말풍선
  }},
  "card5": {{
    "pre_title": <FieldValue>,     // 마무리 카드 소제목
    "main_title": <FieldValue>,    // 마무리 카드 메인 슬로건 (20자 이내)
    "cta": <FieldValue>,           // CTA 문구 (예: "자세한 내용은 영상으로 확인하세요")
    "team_name": <FieldValue>      // 연구팀/기관 이름 (마무리용)
  }},
  "layout_variants": {{
    "1": "A", "2": "B", "3": "B", "4": "D", "5": "A"
  }}
}}

## FieldValue 스키마

각 <FieldValue> 자리는 다음 구조로 채운다:
{{
  "value": "실제 텍스트 내용",
  "confidence": "high" | "medium" | "low",
  "match_quality": "exact" | "normalized" | "fuzzy" | "semantic" | "failed",
  "claim_type": "quantitative" | "qualitative" | "causal",
  "source": {{
    "section": "원문 섹션명 (예: Results)",
    "page": 페이지번호(정수)
  }},
  "risk_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "verified": false
}}

risk_level 자동 판정:
- quantitative + failed → CRITICAL
- fuzzy 또는 semantic → HIGH
- normalized → MEDIUM
- exact 또는 qualitative → LOW
"""
```

### 5-5. LLM 호출 설정

```python
# backend/agents/s6_card_json.py
class S6CardJsonAgent(BaseAgent[S6Input, S6Output]):
    async def execute(self, input_data: S6Input) -> S6Output:
        section_map_text = self._format_section_map(input_data.section_map)

        for attempt in range(3):
            response = await llm_client.messages.create(
                model=config.LLM_MODEL,
                max_tokens=8000,
                system=SYSTEM_PROMPT,
                messages=[{
                    "role": "user",
                    "content": USER_PROMPT_TEMPLATE.format(
                        section_map_text=section_map_text,
                        title=input_data.paper_metadata.title or "unknown",
                        authors=", ".join(input_data.paper_metadata.authors),
                        year=input_data.paper_metadata.year or "unknown",
                        doi=input_data.paper_metadata.doi or "unknown",
                    )
                }],
            )

            try:
                card_data = CardEditorData.model_validate_json(
                    self._extract_json(response.content[0].text)
                )
                critical_count = self._count_risk(card_data, "CRITICAL")
                high_count = self._count_risk(card_data, "HIGH")
                return S6Output(
                    card_data=card_data,
                    critical_count=critical_count,
                    high_count=high_count,
                )
            except (ValueError, KeyError) as e:
                if attempt == 2:
                    raise RuntimeError(f"ERR-S6-001: {e}")
                continue
```

### 5-6. 필드별 그라운딩 가이드

| 필드 | 기대 내용 | 원문 위치 힌트 | 수치 여부 |
|------|-----------|---------------|-----------|
| `meta.org` | 기관명 전체 | 논문 소속(Affiliation), 감사(Acknowledgement) | 아니오 |
| `meta.dept` | 연구 부서/팀 | 소속 상세, 연구비 감사 | 아니오 |
| `meta.researcher` | 교신저자 또는 제1저자 | 저자 목록 | 아니오 |
| `meta.month` | 논문 게재/접수 월 | 저널 날짜, 온라인 공개일 | 아니오 |
| `card1.title` | 핵심 기술 이름 (20자 이내) | 제목, Abstract 첫 문장 | 아니오 |
| `card2.intro` | 사회적 문제 배경 | Introduction §1 | 아니오 |
| `card3.achievement` | 핵심 성과 + 수치 | Results, Abstract (수치 있을 가능성 높음) | **권장** |
| `card4.result` | 비교 결과 수치 | Results, Conclusion | **필수** |
| `card5.main_title` | 마무리 슬로건 | 직접 추출 어려움 → qualitative 허용 | 아니오 |

> `card4.result`에 수치 없으면 CRITICAL 처리. 에디터에서 사용자가 직접 입력해야 함.

### 5-7. S6 금지 사항 (코드에서 검증)

```python
# S6Output 반환 전 후처리 검증
def _validate_grounding(self, card_data: CardEditorData) -> list[str]:
    warnings = []
    for field_name, fv in self._iter_field_values(card_data):
        # 수치가 포함된 value인데 match_quality=failed → CRITICAL 확인
        if self._contains_number(fv.value) and fv.match_quality == "failed":
            if fv.risk_level != "CRITICAL":
                warnings.append(
                    f"[BUG] {field_name}: quantitative+failed but risk_level={fv.risk_level}"
                )
        # verified가 True로 초기화된 경우 → 강제 False
        if fv.verified:
            fv.verified = False
            warnings.append(f"[RESET] {field_name}: verified forced to False")
    return warnings
```

---

## 6. S7 — PNG Renderer

**파일**: `backend/agents/s7_renderer.py`

### 6-1. 계약

| 항목 | 내용 |
|------|------|
| 입력 | `S7Input(job_id, card_data)` |
| 출력 | `S7Output(images, warnings)` — `images: list[bytes]` (길이 1~5) |
| 실패 유형 | **논블로킹** — 개별 카드 타임아웃 시 해당 카드 skip, 나머지 계속 |
| 의존성 | `playwright.async_api`, `docs/08_design_spec.md` 기반 HTML 템플릿 |

### 6-2. 처리 흐름

```
1. Playwright 브라우저 컨텍스트 시작 (재사용 가능한 browser 인스턴스)

2. card_data에서 layout_variants 읽기 → 각 카드의 레이아웃 타입 결정
   (CoverCard → Type A, TextCard → Type B, ... 08_design_spec.md §5-0 참고)

3. 카드별 순차 렌더링 (병렬 미적용 — 메모리 제한):
   for card_num in range(1, 6):
     a. CardEditorData에서 해당 카드 필드 추출
     b. FieldValue.value만 평탄화 (plain string)
     c. HTML 템플릿 렌더링 (Jinja2 또는 f-string)
        - --theme-primary: card_data.theme.primary 주입
        - 레이아웃 타입에 맞는 CSS 클래스 적용
     d. Playwright page.set_content(html) + page.screenshot(...)
        viewport: 1080×1080, device_scale_factor=1
     e. 타임아웃(15초) 초과 시 warnings에 추가, images에 None 대신 skip

4. 브라우저 컨텍스트 닫기

5. S7Output(images=렌더링된 bytes 목록, warnings) 반환
   images 길이 < 5이면 warnings에 "partial render" 추가
```

### 6-3. 구현 제약

```python
# playwright 설정
PAGE_VIEWPORT = {"width": 1080, "height": 1080}
CARD_TIMEOUT_MS = 15_000   # config.PLAYWRIGHT_TIMEOUT_MS

# 스크린샷 설정
screenshot_opts = {
    "type": "png",
    "clip": {"x": 0, "y": 0, "width": 1080, "height": 1080},
    "full_page": False,
}
```

- HTML 템플릿은 `backend/templates/card_{type}.html` 형태로 관리
- CSS 변수 `--theme-primary`는 렌더링 시 `<style>:root{--theme-primary: #xxx;}</style>`로 주입
- 폰트 파일(Pretendard)은 `frontend/public/fonts/`에서 `@font-face`로 로드

---

## 7. S8 — Output Packaging

**파일**: `backend/agents/s8_packaging.py`

### 7-1. 계약

| 항목 | 내용 |
|------|------|
| 입력 | `S8Input(job_id, card_data, images, warnings)` |
| 출력 | `S8Output(job_id, status)` |
| 실패 유형 | **항상 실행** — 내부 실패 시 status=ERROR로 기록하고 반환 |
| 의존성 | `db`, `zipfile` (stdlib) |

### 7-2. 처리 흐름

```
1. card_data를 JSON으로 직렬화 → SQLite card_data 테이블 upsert

2. images를 SQLite card_images 테이블에 저장
   images가 부분적이면 (일부 카드 실패) 있는 것만 저장

3. ZIP 생성
   파일명 규칙: polyinsight_{slug}_{YYYYMM}.zip
   slug = card_data.card1.title.value를 ASCII로 슬러그화 (최대 40자)
   내용:
     card_01.png ... card_05.png (렌더링된 것만)
     card_data.json (CardEditorData 전체)

4. ZIP bytes → SQLite exports 테이블 저장
   expires_at = now() + 24h

5. job 상태 업데이트
   images 전부 성공 → status=DONE
   images 부분 성공 → status=DONE, warnings에 "partial render" 포함
   card_data 없음 → status=ERROR

6. S8Output(job_id, status) 반환
```

### 7-3. TTL 클린업

```python
# S8 완료 후 백그라운드 태스크로 등록
async def cleanup_expired_blobs(db_conn):
    cutoff = datetime.utcnow() - timedelta(hours=24)
    await db_conn.execute(
        "UPDATE card_images SET png_bytes = NULL WHERE rendered_at < ?",
        (cutoff.isoformat(),)
    )
    await db_conn.execute(
        "UPDATE exports SET zip_bytes = NULL WHERE expires_at < ?",
        (datetime.utcnow().isoformat(),)
    )
```

---

## 8. Degraded Mode 전파 규칙

| 발생 지점 | 전파 방향 | 영향 |
|-----------|-----------|------|
| S2 `degraded_mode=True` | → S6 S6Input에 포함 | S6는 모든 필드 `confidence="low"` 강제 |
| S6 `critical_count > 0` | → 프론트엔드(API 응답) | ActionBar "내보내기" 버튼 비활성화 |
| S6 `high_count > 0` | → 프론트엔드(API 응답) | ActionBar "내보내기" 버튼 비활성화 |
| S7 부분 렌더링 | → S8 `warnings` 포함 | ZIP에 누락 카드, `partial render` 경고 |

**Degraded → 정상 전환 방법**: 사용자가 에디터에서 CRITICAL/HIGH 필드를 직접 수정하고 `verified=True`로 변경하면 ActionBar가 활성화된다.

---

## 9. LLM 클라이언트 공통 설정

```python
# backend/core/llm_client.py
import anthropic

client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

# S6 전용 — 프롬프트 캐싱 적용 (section_map은 per-call, system prompt는 캐시)
# Anthropic prompt caching: system prompt에 cache_control 지정
CACHED_SYSTEM = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"}
    }
]

# 재시도 설정 (지수 백오프)
RETRY_DELAYS = [0.5, 1.0, 2.0]   # 초 단위
MAX_RETRIES = 3
```

- S2 LLM 폴백은 캐싱 없이 단순 호출
- S6는 system prompt 캐싱 적용 (section_map이 길어 입력 토큰 절감 효과 큼)

---

## 10. 변경 이력

| 날짜 | 버전 | 변경 내용 |
|------|------|-----------|
| 2026-05-11 | v1.0 | 최초 작성. S1~S8 에이전트 계약 전체, S6 프롬프트 초안 포함. |
