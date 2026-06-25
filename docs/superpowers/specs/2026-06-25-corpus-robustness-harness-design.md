# 코퍼스 견고성 하니스 — 설계 (측정·학습 기반)

> 2026-06-25 | 브레인스토밍 산출물
> 상태: 설계 승인 대기 → writing-plans 전 단계

---

## 1. Problem

PolyInsight은 결국 **모든 저널에서 발행된 논문**을 입력으로 받는다. 그러나 지금
파이프라인이 *야생 논문에 얼마나 견디는지 측정할 방법이 없다* — 코퍼스도, 배치 실행도
없이 박사님이 웹에서 한 편씩 수동 업로드하는 게 전부다. 한 편씩으로는 "모든 저널"
스케일의 실패 모드를 절대 따라잡지 못한다.

오늘(2026-06-25) "Attention Is All You Need" 실호출이 셀룰로오스 논문엔 없던 S6 버그
2개를 노출한 것이 그 증거다([[project_s6_pipeline_hardening]]). 반응형(논문마다 깨지면
고침)은 한 저널엔 통해도 모든 저널엔 안 통한다.

**관찰된 실패 지점 지도** (실제 코드 기준):

| 단계 | 야생 논문이 깨지는 양상 | 비용 |
|---|---|---|
| **S1 추출** | 스캔본(이미지 PDF)·깨진 폰트 → 텍스트 거의 안 나옴. OCR 없음 | $0 (LLM 미사용) |
| **S1 섹션파싱** ⚠️ | `_parse_sections`가 pymupdf4llm Markdown 형식(`## **N. Name**`)에 강결합. 다른 저널 조판/2단/비라틴 → 헤더 0개 → `full_text` degraded | $0 |
| **S6 생성** | LLM 응답 변이(스키마·커버리지·게으름) | ~$0.10/편 |
| **S7 렌더** | 우리 JSON을 렌더 → 야생 민감도 낮음 | $0 |

> **드리프트 기록**: CLAUDE.md·docs는 "S2 Section Parsing"을 별도 단계로 적었으나
> 실제 파이프라인은 **S1→S6→S7→S8**이고 섹션파싱은 S1의 `_parse_sections`에 흡수돼 있다.
> 이 spec은 실제 코드를 기준으로 한다.

---

## 2. Scope — 이건 프로젝트가 아니라 프로그램의 첫 하위 프로젝트

"모든 야생 논문 견고성"은 프로그램이다. 이 spec은 그 **첫 하위 프로젝트 = 측정·학습 기반**만
다룬다. 측정 없이는 아래 둘(섹션파싱 일반화, OCR 등)을 고쳐도 나아졌는지 모른다.

**핵심 통찰 — 단계별 비용 비대칭**: S1(추출+섹션)은 LLM을 안 써서 **공짜**, S6은 돈.
가장 큰 fragility(섹션파싱)가 공짜 단계에 있으므로 측정 전략이 이를 활용해야 한다.

박사님 어휘(채택):
- **S1 배치 = 두더지 잡기(whack-a-mole)**: 대량 야생 코퍼스를 사정없이 밀어넣어 파서
  예외처리를 갈고닦음. 정답 없음, 비용 $0 → 대량으로.
- **S6 배치 = 회귀 테스트(regression)**: 조판·도메인 골고루 섞인 **Golden 8**을 꾸준히
  돌려 프롬프트·스키마 변이를 잡음. 비용 발생 → 소수 엄선.

---

## 3. Architecture — 단계 분리 하니스

`backend/scripts/corpus_harness.py` — **오프라인 개발 도구**(웹/에디터/프로덕션 무관).

```
모드 A (whack-a-mole, 무료):  --stage s1   --corpus <folder>
  폴더의 모든 PDF → S1만 실행 → degrade 텔레메트리 집계
  → 리포트: 추출실패 N / 섹션0개 M / layout별·code별 집계

모드 B (regression, 유료):     --stage full --corpus <golden-folder>
  Golden 8 → S1→S6 → 구조 불변식 검증
  → 리포트: 어느 논문 / 어느 불변식 / 어느 layout 위반
```

- 한 스크립트, 플래그 분기. **기본은 모드 A(무료)**. 모드 B는 실 LLM 호출이라
  **항상 사전 허락**([[feedback_ask_before_paid]]) — 스크립트가 실행 전 확인/명시 요구.
- S7(렌더)은 측정 대상 아님(우리 JSON 렌더 → 야생 민감도 낮음). 모드 B도 S6까지만.

---

## 4. Component — 구조화된 degrade 텔레메트리

지금 파이프라인은 degrade 이유를 자유 텍스트 `warnings: list[str]`로 흘린다. 85편을
regex로 긁어 집계하는 건 brittle(측정 기반이 측정 자체가 부실한 모순)하고, `warnings`는
이미 status API로 프론트에 배선된 **유저향 채널**이라(`jobs.py:69`) 엔지니어링 코드를
섞으면 SoC 위반(나중에 프론트가 regex로 접두사 잘라내야 함).

**결정 — 타입드 enum + 구조화 필드(유저향 warnings와 분리)**:

```python
# core/models.py — 단일 출처. 린터/타입체커가 모든 참조 검증(오타 silent-skip 불가).
class DegradeCode(StrEnum):
    S1_NO_SECTIONS     = "s1_no_sections"
    S1_LOW_WORDS       = "s1_low_words"
    S1_EXTRACT_FAILED  = "s1_extract_failed"
    S1_PARSE_FALLBACK  = "s1_parse_fallback"
    S6_COVERAGE_MISMATCH = "s6_coverage_mismatch"
    S6_SCHEMA_INVALID    = "s6_schema_invalid"
    S6_TRUNCATED         = "s6_truncated"
    # 야생에서 새 실패 모드 만나면 enum 멤버 추가 = 두더지 명명(린터가 전 참조 검증)

class DegradeEvent(BaseModel):
    code: DegradeCode
    layout: str | None = None   # template_type. 카탈로그 취약성 집계의 축.
    detail: str = ""            # card_num·추출단어수 등 사람용 부연(집계엔 안 씀)
```

- 각 단계 출력(S1Output/S6Output)에 `degrade_events: list[DegradeEvent]` **추가**.
  `warnings`는 순수 유저향 문장으로 정화.
- **`layout`이 `page_idx`가 아닌 이유**: 위치 인덱스는 논문마다 다른 레이아웃을 가리킨다
  (A논문 idx3=compare_table, B논문 idx3=timeline). 박사님 목표는 "**어느 레이아웃이
  취약한가**"이므로 `GROUP BY layout`이 정답. 위치로 묶으면 레이아웃이 뭉뚱그려진다.
- 카드-로컬 실패(Writer 루프의 특정 카드 필드 검증)는 그 순간 `beat_types[card_num]`로
  layout을 안다 → 태깅. 덱-전역 실패(커버리지·meta·전체 JSON)는 layout=None, code 자체가
  자기-위치설명.
- **필드 추가 금지(미니멀)**: `severity`·`timestamp` 등 미리 X. `code`+`layout`+`detail`이면
  v1 충분, 필요해지면 그때(박사님 "미리 방어 금지" 철학).

---

## 5. Component — 코퍼스 & Golden Dataset

**whack-a-mole 코퍼스**: 이미 존재한다 —
`C:\Users\User\Desktop\한국생산기술연구원_근로장학\poly_claude_code\논문` 폴더 **85편**,
다양성 양호(arXiv 1단, Elsevier/Wiley 2단, bioRxiv 프리프린트, 물성·화학, 초단편 합성 스텁,
물리). v1은 이 폴더를 가리킨다. arXiv/PMC 자동수집은 **볼륨 확장용 후속 옵션**(v1 불필요).
이 코퍼스는 **무주석** — degrade 텔레메트리가 알아서 집계하므로 20→100편으로 커져도
큐레이션 노동 0.

**Golden Dataset**: 박사님이 위 85편에서 **조판·도메인 골고루 8편 엄선** + 논문별 기대치.
설계상 작게 고정(회귀 집합이지 커버리지 집합 아님 — 커우는 게 아니라 교체/회전).

```yaml
# golden/expectations.yaml  (논문당 한 줄 수준 — 최소)
- file: Transformer_Attention_Is_All_You_Need.pdf
  expected_min_cards: 6        # 밀도 높은 논문이 3장으로 쪼그라들면 fail
- file: agr_01_crispr_drought_wheat.pdf
  expected_min_cards: 3        # 초단편은 적게가 정상
```

> **왜 `expected_layouts`(특정 레이아웃 못박기)를 안 쓰는가**: 긍정적 표류 역설.
> 내일 더 똑똑한 프롬프트가 compare_table보다 terminal_block+timeline로 *더 잘* 풀어내면,
> 레이아웃을 못박은 불변식이 그 좋은 결과를 "회귀"로 죽인다 = 스냅샷 지옥의 변장.
> **테스트는 identity가 아니라 property를 향한다**(§7 다양성 바닥선으로 대체).

---

## 6. Component — 모드 A 리포트 (whack-a-mole)

S1만 85편 실행 → `degrade_events` 집계:

```
=== S1 견고성 리포트 (85편) ===
EXTRACT_FAILED   : 3편  [scan_a.pdf, scan_b.pdf, ...]
NO_SECTIONS      : 14편 [2단 조판 다수 — 저널별]
LOW_WORDS        : 2편
정상(섹션 추출됨) : 66편 (78%)
--- 파일별 상세 ---
1-s2.0-S2666...  : NO_SECTIONS  (Elsevier 2단)
...
```

목적: "어느 조판/저널에서 섹션파싱이 가장 많이 깨지나"를 데이터로 보고 **핀셋 수정**.
$0이므로 파서 고칠 때마다 무한 반복 실행.

---

## 7. Component — 모드 B 회귀 판정 (Golden 8, 유료)

**제약**: S6는 LLM(temp 0.2)이라 비결정적 — 출력 정확 비교(스냅샷)는 매번 false positive →
**불변식(invariant) 검증**: LLM이 문구를 어떻게 쓰든 *반드시 성립해야 하는 성질*만 단언.
유지할 베이스라인 없음(절대규칙 + 논문별 최소 기대치) → 스냅샷 관리 지옥 회피.

**모드 B는 골든 논문당 3결과를 구분**(오늘 fail-fast 도입 이후 하드 실패는 *예외*로 옴):
1. **예외 raise**(ERR-S6-001/002 등 하드 실패: 스키마·커버리지·truncation) → `code`로 환원해 **failure** 기록. 출력 없음 → 불변식 검증 생략.
2. **반환 + degrade_events 존재**(soft degrade: safe_fallback→callout 등) → degrade 기록 + 불변식 검증.
3. **반환 + clean** → 아래 4층 불변식 검증.

**v1 판정 = 4층 결정론적 불변식** (전부 LLM-judge 불필요):

| 층 | 불변식 | 막는 허점 |
|---|---|---|
| 구조 | 카드 수 유효·first=cover_v2·last=closing_v2·커버리지=스토리보드·template_type 유효·meta 파싱 | 크래시·스키마 붕괴 |
| 콘텐츠-새너티 | 필드별 최소 길이·플레이스홀더 블록리스트(`"N/A"`,`"해당 사항 없음"`,`"."`,`"-"`)·**exact 중복 + Jaccard 토큰 중복도** 임계 | 플레이스홀더 쓰레기·동의어 패딩(거친 것) |
| 다양성 바닥선 | distinct 레이아웃 ≥ N (양성 핀 ❌) | Monochrome Syndrome(전부 reasons/callout 도배) |
| per-golden | `expected_min_cards` 충족 | 카드 수 압축(7→3 정보유실) |

임계값(최소 길이, Jaccard 컷, distinct 바닥선 N)은 **Golden 8에 대해 캘리브레이션** —
정상 8편이 전부 통과하는 가장 빡빡한 값으로 튜닝.

**리포트**: `golden_A.pdf / 다양성 바닥선 위반 / layout=reasons×5` 처럼 논문·불변식·layout 짚음.

---

## 8. Out of Scope / Deferred

명시적으로 v1에서 제외(끝없는 epicycle 방지). 판정 원칙: **결정론적·쌈 → v1 / 의미판단 → 후속.**

- **의미 품질 LLM-judge 계층**: "이 헤드라인이 스크롤 멈추는 좋은 훅인가 / 재작성이 원문에
  충실하면서 매력적인가 / *영리한* 저-중복 패러프레이즈 패딩". 이건 의미판단이라 judge/사람
  필요. **근본 진실**: 충분히 영리하게 게을러진 LLM은 어떤 결정론적 체크도 게임한다 —
  v1=싸게 gross 80% / judge=비싸게 subtle 20%. v1을 방탄으로 위장하지 않는다.
- **arXiv/PMC 자동수집**: 볼륨 확장용. 85편으로 v1 시작.
- **OCR**(스캔본 추출): EXTRACT_FAILED를 *측정*은 하되 *해결*은 후속 하위 프로젝트.
- **섹션파싱 일반화**(2단/비라틴 조판): 모드 A가 노출할 두더지. 수정은 측정 다음 단계.

---

## 9. 결정 로그 (거절된 대안 — 같은 논쟁 반복 방지)

| 결정 | 채택 | 거절 + 이유 |
|---|---|---|
| 실행 전략 | 단계 분리(S1 대량 무료 / Golden 8 유료) | 전체 일괄(돈 낭비: 섹션파싱 측정에 S6 비용 기여 0) · S1-only(S6 회귀 영영 방치) |
| 측정 신호 | 단계별 degrade 텔레메트리 | 이진 성공/실패(왜 깨졌나 모름) · 출력 품질 점수(비용·주관, 후속) |
| degrade 구조 | 타입드 enum + 구조화 필드 | 접두사 문자열 컨벤션(string-ly typed: 오타 silent-skip, SoC 위반) · 하니스가 자유텍스트 regex(brittle) |
| 위치 필드 | `layout`(template_type) | `page_idx`(위치 인덱스 → 레이아웃 뭉뚱그림) |
| 회귀 판정 | 4층 결정론 불변식 | 스냅샷 정확비교(LLM 비결정성→false positive 지옥) · 크래시만(품질 붕괴 못 잡음) |
| 다양성 검증 | property(distinct 바닥선) | identity(`expected_layouts` 못박기 → 긍정적 표류를 회귀로 죽임) |
| 중복 검증 | exact + Jaccard 토큰중복 | exact만(패러프레이즈에 뚫림) |

---

## 10. Risks

- **캘리브레이션 리스크**: 불변식 임계가 너무 빡빡하면 정상 골든도 fail(false alarm),
  너무 느슨하면 §7 허점이 다시 샌다. → Golden 8 정상통과를 기준으로 보수적 튜닝, 야생에서
  새 우회 발견 시 조임.
- **Golden 8 대표성**: 8편이 조판·도메인을 못 덮으면 회귀가 일부 변이를 놓침. → 박사님이
  의도적으로 다양하게 선별(2단·1단·단편·장편·도메인 믹스).
- **degrade_events 계약 추가**: S1Output/S6Output 스키마 변경 → docs/05·07 갱신 필요
  (docs-before-code). 오케스트레이터 passthrough도 추가.

---

## 11. Open Items (박사님 입력 필요)

1. **Golden 8 선별**: 85편 폴더에서 8편 + 각 `expected_min_cards`. (저작권·도메인 판단은
   박사님 영역 — 코드가 못 정함.)
2. **모드 B 첫 실행 사전 허락**: 유료. 캘리브레이션 1회분 비용 발생.

---

## 12. 구현 터치포인트 (writing-plans에서 상세화)

- `core/models.py`: `DegradeCode`(StrEnum) + `DegradeEvent` + S1Output/S6Output에 `degrade_events`
- `agents/s1_extractor.py`: 각 degrade 분기점에서 `DegradeEvent` emit (warnings 정화)
- `agents/s6_card_json.py` · `s6/writer.py`: S6 degrade 분기점 emit (layout 태깅)
- `agents/orchestrator.py`: degrade_events passthrough
- `backend/scripts/corpus_harness.py`(신규): 모드 A/B CLI + 리포트
- `backend/scripts/golden/expectations.yaml`(신규): Golden 8 기대치
- 불변식 모듈(신규, 예: `scripts/invariants.py` 또는 하니스 내부): 4층 검증
- docs/05·07: degrade_events 계약 반영 (docs-before-code)
- docs/04: 파이프라인 실제 단계(S1→S6, S2 흡수) 드리프트 정정
