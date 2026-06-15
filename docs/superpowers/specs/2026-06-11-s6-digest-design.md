# S6 논문이해팀(다이제스트) 슬라이스 설계

> 2026-06-11 · PolyInsight
> Problem / Decision / Rationale / Risks 형식
> 선행: docs/superpowers/specs/2026-06-10-multiagent-s6-design.md (S6 멀티에이전트 분해)

---

## Problem

S6 멀티에이전트 분해 이후, **Architect(Sonnet)가 raw section_map(≤50k)을 직접 읽는다.**
Sonnet은 토큰 단가가 높아, 잡당 1회라도 50k 입력은 비용의 큰 부분이다(full E2E ~43s).
또한 Architect·Writer가 각자 raw에서 내용 모양(수치·비교·용어·그림)을 매번 다시 추론하므로,
레이아웃 판단·grounding의 재료가 구조화돼 있지 않다.

## Decision

Architect 앞에 **논문이해팀 Understand(Haiku)** 단계를 삽입한다. Understand가 raw를
**구조화된 내용모양 인벤토리(PaperDigest)**로 압축하면:

- **Architect(Sonnet)는 작은 다이제스트만 읽는다** → 비용↓ (핵심 이득).
- 다이제스트의 각 필드가 특정 레이아웃과 대응 → 레이아웃 판단 재료가 명시적.
- 수치·주장에 source{section,page}가 달려 Writer의 grounding 힌트가 된다.

### 1차 동력 = 품질 우선

구조화 추출로 Architect의 레이아웃 판단과 Writer의 grounding을 좋게 하는 것이 목적이다.
비용 절감(Sonnet 입력 압축)은 부수 이득으로 간주한다.

### grounding 입장 (fidelity)

- **Architect = 다이제스트만** 읽는다(레이아웃만 결정, 사실을 쓰지 않으므로 무방).
- **Writer = 다이제스트(힌트) + raw section_map(권위)**. 수치·출처는 raw에서 최종 확인.
  CLAUDE.md "파생 요약을 원문보다 권위 있게 다루지 마라"를 지킨다.
- 이 입장 덕에 **다이제스트 추출 오류는 하류(Writer의 raw 검증)에서 잡힌다** →
  다이제스트는 힌트일 뿐이라 Understand를 Haiku로 둬도 안전하고, 그래야 비용 이득이 실현된다.

### 계약 동결 + S6 내부

`S6Input → S6Output`은 동결. Understand는 architect/writer와 같은 S6-내부 모듈이고,
코디네이터(`S6CardJsonAgent`)가 중계한다(모듈끼리 직접 호출 금지, CLAUDE.md §4).

## 데이터 흐름

```
Understand (Haiku, raw 50k) ──→ PaperDigest
        │
        ▼
Architect (Sonnet, 작은 다이제스트) ──→ Storyboard       ← 비용 이득
        │
        ▼
Writer (Haiku, raw + 다이제스트 힌트) ──→ cards + signals  ← grounding=raw 권위
        │
[피드백 루프 1회 — 변경 없음] → Verify(코드) → S6Output
```

### degraded fallback (CLAUDE.md §6)

Understand가 최종 실패하면 → **Architect가 raw section_map을 읽는 현재 동작으로 폴백** +
`warnings`에 degraded 표기. 다이제스트는 품질 향상이지 하드 의존이 아니다.
Architect 모듈은 하위호환: digest 있으면 digest 모드, 없으면 section_map 모드(현행).

## PaperDigest 스키마 (내용모양 인벤토리)

각 필드가 특정 레이아웃과 대응. 수치·비교·주장은 source{section,page}를 단다(grounding 힌트).

```python
class DigestNumber:     value, unit, label, context, source   # → bigstat/multistat
class DigestComparison: attribute, items[], values[], source  # → compare_table
class DigestTerm:       term, plain                           # → definition
class DigestFigure:     ref, shows                            # → image_hero
class DigestClaim:      role(problem|innovation|result|application|method), text, source  # → 스파인
class PaperDigest:
    one_liner: str
    numbers:       list[DigestNumber]
    comparisons:   list[DigestComparison]
    terms:         list[DigestTerm]
    figures:       list[DigestFigure]
    process_steps: list[str]
    claims:        list[DigestClaim]
    domain_hint:   str
```

다이제스트 = 원재료 재고(무엇이 있나), Architect = 편집 결정(무엇을 어떤 순서·레이아웃으로).

## 계약

**새 내부 타입 (`backend/core/models.py`):**
```python
PaperDigest (+ DigestNumber/Comparison/Term/Figure/Claim)
class UnderstandInput:  section_map, paper_metadata
# UnderstandOutput = PaperDigest 직접 반환
```
**기존 타입 확장 (하위호환, 기본 None):**
```python
ArchitectInput: + digest: PaperDigest | None = None
WriterInput:    + digest: PaperDigest | None = None
```
**모듈 계약:**
- `Understand.run(UnderstandInput) → PaperDigest` (Haiku)
- `Architect.run` — digest 있으면 다이제스트를 source material로, 없으면 raw(폴백). SEQUENCING_RULES 그대로.
- `Writer.run` — raw(권위) + digest(힌트) 둘 다 프롬프트에.

## 프롬프트 (`s6/prompts.py` 추가)

- `UNDERSTAND_SYSTEM/USER` — 추출 전용: 원문에서 수치(+섹션·페이지)·비교쌍·전문용어·그림·
  공정단계·역할별 핵심주장을 JSON으로. 없는 건 빈 배열. 지어내지 마라. 상위 N개로 제한.
- `ARCHITECT_USER` — digest 모드 분기: raw 대신 다이제스트를 "내용모양 인벤토리"로 포맷해 주입.
- `WRITER_USER` — 기존 raw 블록 + "사전 추출 힌트(수치·출처·용어)" 블록 추가.

## 에러 / degraded

| 상황 | 처리 |
|---|---|
| Understand 503/일시 실패 | `_with_retries` 재시도 |
| Understand 최종 실패 | degraded 폴백 — Architect가 raw 읽음 + warnings에 "다이제스트 생략—원문 직접" |
| Understand 출력 천장 | 다이제스트 상위 N개 제한(프롬프트), 그래도 잘리면 degraded 폴백 |
| Architect/Writer | 기존 그대로(ERR-S6-001/002/003) |

## 테스트 / A/B 검증

- **단위:** Understand가 PaperDigest 스키마 파싱(numbers가 source 보유), model=Haiku.
  Architect digest 모드 → storyboard. Architect 폴백(digest None → section_map). Writer digest+raw.
  코디네이터가 understand→architect→writer 배선 + Understand 실패 시 폴백.
- **A/B 게이트** (`s6_gate.py ab`) — 고정 논문으로 다이제스트 ON/OFF 둘 다 실행 비교:
  1. **비용** — Architect user-prompt 길이(Sonnet 입력 프록시): OFF≈50k자 → ON≈수천자.
  2. **grounding** — CRITICAL 수 미증가.
  3. **레이아웃** — 확장 레이아웃 수 ON ≥ OFF.
  4. **다이제스트 충실** — numbers/comparisons/terms 비어있지 않음.
- **회귀:** 기존 backend pytest + web tsc/vitest 그대로 통과(digest는 옵셔널 추가).

> 합격 기준(정직): 1차는 **비용↓ + grounding 비퇴행 + 다이제스트 채워짐**으로 잡는다.
> 한 논문에선 품질차가 작을 수 있어(OFF도 이미 확장 2개) 품질 우위는 관측치로 기록, 과한 단정 금지.

## 범위 (YAGNI)

- ✅ Understand 모듈 + PaperDigest + Architect/Writer digest 모드 + 폴백 + A/B 게이트
- ❌ figure→이미지 파이프라인(image_hero는 업로드 슬롯 의존, 별개 작업)
- ❌ DEV_MOCK에 digest 별도 mock 안 만듦 — mock 경로는 기존처럼 architect/writer mock 직행(Understand 건너뜀)
- ❌ domain_hint로 theme 자동화 변경 안 함(현행 Architect theme 유지)

## docs 영향

계약(S6Input/Output) 동결. `docs/05_agent_design.md` S6 섹션에 Understand 단계 추가,
`docs/04_architecture.md` 다이어그램 갱신. CLAUDE.md §7 docs-먼저 순서 준수.

## Risks

- **지연 증가:** LLM 호출이 2개→3개(순차)로 늘어 latency↑(~43s → ~60s 추정). 사용자는 처리
  오버레이를 보므로 수용 범위. A/B에서 실측해 기록.
- **다이제스트 추출 누락:** Haiku가 중요한 수치·비교를 빠뜨리면 Architect 판단 재료가 준다.
  단 Writer가 raw를 보므로 본문 fidelity는 보존. 누락은 품질(레이아웃 적절성) 문제지 fidelity 문제 아님.
- **출력 천장:** 다이제스트가 크면 Haiku 8192에서 잘릴 수 있음. 상위 N개 제한으로 완화, 잘리면 폴백.
- **품질 이득 미입증 가능성:** 단일 논문 A/B에서 품질차가 안 보일 수 있음. 비용·grounding은
  확실히 측정되므로 1차 합격엔 충분. 품질은 후속 다논문/실유저로.
- **이중 입력 모드 복잡도:** Architect가 digest/section_map 두 모드 → 분기. 폴백 견고성의 대가.
