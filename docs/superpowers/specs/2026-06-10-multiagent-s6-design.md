# S6 멀티에이전트 분해 설계

> 2026-06-10 · PolyInsight
> Problem / Decision / Rationale / Risks 형식

---

## Problem

S6는 현재 **단일 모놀리식 LLM 호출**(Haiku)로 세 가지 일을 한 번에 한다:
스토리보드(레이아웃 결정) → 콘텐츠 작성 → grounding 채점.

"내용 모양 → 레이아웃 선택"을 담당하는 **레이아웃 뇌**(`_SEQUENCING_RULES`,
`s6_card_json.py:90-112`)가 Haiku에서 작동하지 않는다. 고정 논문(키토산)으로
두 차례 프롬프트를 다듬어 실행했으나, 확장 레이아웃(multistat/compare_table/
definition/quote)이 **0개** 등장했다 — Haiku가 multistat 후보가 명백한
경우에도 캐논 기본값(bigstat)을 골랐다. 단일 거대 프롬프트가 판단·작성·채점을
동시에 떠안아 각 일을 충분히 잘 못한다.

## Decision

S6 **내부**를 전문화된 에이전트(팀)로 분해하고, 팀별로 적합한 모델을 라우팅한다.

### 핵심 프레이밍 — 멀티에이전트는 S6 내부 구조

파이프라인 계약(`S6Input → S6Output`)은 **동결**한다. CLAUDE.md 불변식
("오케스트레이터가 유일한 파이프라인 컨트롤러, 에이전트는 서로 직접 호출 금지")을
지키기 위해:

- 파이프라인 오케스트레이터는 여전히 `S1 → S6 → S7 → S8` 하나의 S6만 본다.
- S6 *안에서* Architect/Writer가 모듈로 분리되고, S6가 둘을 **국소 조율**한다.
  두 모듈은 서로 직접 호출하지 않고 S6를 거친다 → 불변식 정신 유지.
- 추후 별도 스테이지(S6a/S6b)로 승격하려면 그때 오케스트레이터로 올린다.
  지금은 가설검증이 우선이라 S6 내부로 둔다.

### v1 에이전트 명단

| 팀 | 모듈 | 모델 | 책임 | 안 하는 것 |
|---|---|---|---|---|
| **설계팀 Architect** | `s6/architect.py` | **Sonnet** | section_map → **Storyboard만**(beats: template_type·역할·핵심메시지·내용모양 근거) + 추천 테마. 레이아웃 뇌 격리 | 카드 본문 안 씀 |
| **콘텐츠팀 Writer** | `s6/writer.py` | **Haiku** | Storyboard + 원문 → 각 카드 fields(grounded·재작성·글자수 상한). fit 안 맞으면 불일치 신호 | 레이아웃 안 정함 |
| **검증팀 Verify** | 기존 `_post_process` | **코드** | match_quality·claim_type → risk_level | 변경 없음 |

### 모델 라우팅 근거

판단 단계(설계)만 Sonnet, 비싼 본문(작성)은 Haiku, 검증은 코드.
v1은 다이제스트가 없어 Architect가 raw section_map(≤50k)을 직접 읽는다 —
입력은 크지만 잡당 1회·출력은 작고(beats만), "약간 비쌈"을 수용해 핵심 가설을
가장 빨리 검증한다.

## 데이터 흐름

```
S6Input(section_map, paper_metadata, card_count)
        │
        ▼
  ┌─────────────┐   ArchitectOutput
  │  Architect  │── = Storyboard(story_arc, beats[]) + recommended_theme
  │  (Sonnet)   │     beat = {card_num, template_type, narrative_role,
  └─────────────┘              key_message, content_shape_reason}
        │
        ▼  (Storyboard 전달)
  ┌─────────────┐   WriterOutput
  │   Writer    │── = cards[](fields) + meta + mismatch_signals[]
  │   (Haiku)   │
  └─────────────┘
        │
        ▼  (불일치 있으면 → 피드백 루프)
  ┌─────────────┐
  │ Verify=코드 │── risk_level 판정 + 밀도 경고
  └─────────────┘
        │
        ▼
  S6Output(card_data=CardEditorData, critical_count, high_count, warnings)
```

### 계약

- **동결:** `S6Input` / `S6Output` 그대로.
- `Storyboard` / `CardStorybeat`는 이미 `models.py`에 존재 →
  `CardStorybeat`에 `content_shape_reason: str` 한 필드만 추가.
- 모듈 계약: `ArchitectInput → Storyboard`, `WriterInput(+Storyboard) → cards + 신호`.
  전부 typed, S6가 중계.

## 피드백 루프 (1회, 오케스트레이터 중계)

**언제:** Writer가 어떤 비트를 채우다 *grounded 내용으로 그 뼈대의 필수 필드를
못 채울 때*. 레이아웃 뇌의 맹점이 실제로 드러나는 지점.

**불일치 신호 (Writer가 비트별로 emit):**
```json
{ "card_num": 4, "mismatch": true,
  "reason": "multistat은 수치 2~4개 필요한데 원문에 grounded 숫자가 1개뿐",
  "suggested_shape": "bigstat_compare" }
```

**루프 (S6 중계, 상한 1회):**
```
Writer 1차 → mismatch_signals 수집
  ├─ 없음 → 바로 Verify로
  └─ 있음 → Architect에 [해당 비트 + reason + suggested_shape]만 전달
            → Architect가 그 비트들의 template_type만 1회 수정 (나머지 비트 동결)
            → Writer가 수정된 비트만 재작성
            → 그래도 불일치? → Writer가 안전 뼈대(statement/callout)로 대체
                              + degraded 경고 1줄 (S6Output.warnings)
```

**안전성:**
- 상한 1회 = 무한루프 불가, 비용 예측가능(최악 = Architect 2회 + Writer 2회).
- Architect는 지목된 비트만 수정 → 전체 스토리 흔들림 없음.
- 끝까지 안 맞으면 억지로 끼우지 않고 안전 뼈대로 내려앉되 degraded로 표면화
  (CLAUDE.md §6: degraded ≠ success).

## v1 범위

- ✅ S6 내부를 Architect(Sonnet) + Writer(Haiku) + 1회 루프 + Verify(기존 코드)로 분리
- ✅ `CardStorybeat`에 `content_shape_reason` 추가, `_SEQUENCING_RULES`를 Architect 전용 프롬프트로 이관
- ✅ DEV_MOCK_LLM 경로 유지 (Architect+Writer 둘 다 결정적 mock)
- ❌ 논문이해 다이제스트 (다음 슬라이스) — v1은 Architect가 raw section_map 직접 읽음
- ❌ 시각팀 LLM화 — 추천테마 → 세트 결정론 유지

## 에러 / degraded (CLAUDE.md §5·6 준수)

| 상황 | 처리 |
|---|---|
| Architect 실패 | 기존 재시도(503 백오프 포함) → 지속 시 `ERR-S6-001` |
| Writer 실패 | 동일 재시도 |
| Writer 출력 천장(card_count 과다) | 기존 `ERR-S6-002`(카드 줄이라) |
| 루프 1회 후 잔여 불일치 | 안전 뼈대 대체 + `warnings`에 "카드N 레이아웃 fit 미해결—안전 뼈대 대체" |
| Architect가 잘못된 template_type | `VALID_TEMPLATE_TYPES` 검증 실패 → 재시도 |

## 테스트

- **단위:** Architect 출력 스키마(beats valid, 첫=cover_v2·끝=closing_v2,
  template_type ∈ VALID), Writer 출력(cards가 beats와 template_type 일치),
  루프(mock 불일치 신호 1개 주입 → Architect 수정 → Writer 재작성 경로).
- **mock 모드:** 기존 `_build_mock_card_data` 결정적 경로 보존.
- **★가설 검증 게이트(이 작업의 진짜 목적):** 고정 논문(키토산) 실행 →
  확장 레이아웃(multistat/compare_table/definition/quote)이 등장하는가.
  Haiku 모놀리식 = 0이었음. Sonnet-Architect에서 ≥1이면 "레이아웃 뇌 작동" 가설 통과.
- **회귀:** 기존 backend pytest 16 + web tsc/vitest 그대로 통과.

## docs 영향

계약(S6Input/Output)은 동결이라 안 바뀜. 단 S6 *내부 설계*가 바뀌므로
`docs/05_agent_design.md`(S6 섹션) + `docs/04_architecture.md`(S6 다이어그램)
업데이트 — CLAUDE.md §7 "docs 먼저" 순서 준수.

## Risks

- **Sonnet 비용:** Architect가 raw 50k를 읽음. 잡당 1회·저빈도라 감내 가능하나,
  다음 슬라이스(다이제스트)로 입력을 압축하면 더 싸진다. 다이제스트는 v1 검증 후.
- **2-호출 지연:** 단일 호출 → 순차 2호출(+최악 루프 2회)로 latency 증가.
  사용자는 처리 중 오버레이를 보므로 수 초 증가는 수용 범위. 측정 후 판단.
- **가설이 틀릴 수 있음:** Sonnet-Architect도 확장 레이아웃을 안 고를 가능성.
  그 경우 분해는 유지하되(클린 기반은 남음) 프롬프트/예시를 보강하거나
  다이제스트가 판단 재료를 더 잘 줄지 검토. 게이트가 이를 조기에 드러냄.
- **승격 부채:** 지금은 S6 내부 조율이라, 추후 별도 스테이지로 올릴 때 리팩터 필요.
  모듈 경계를 깨끗이 두어 비용을 낮춘다.
