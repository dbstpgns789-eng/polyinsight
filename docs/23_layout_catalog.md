# 23. 레이아웃 카탈로그 (Layout Catalog)

> PolyInsight v2.3 | 2026-06-24
> **이 문서는 레이아웃(뼈대)의 단일 정본(DB)이다.** 레이아웃을 추가·변경하려면
> 먼저 이 문서를 고치고, 그 다음 §운영규칙의 전사 순서를 지킨다.
> 구글 시트 카탈로그는 사람이 보는 뷰일 뿐, AI에 도달하는 건 이 문서 → `prompts.py`다.

---

## 0. 왜 이 문서가 필요한가 (Problem)

같은 레이아웃 명세가 코드 5군데에 흩어져 있었다:

| 위치 | 용도 | 읽는 주체 |
|---|---|---|
| `backend/agents/s6/prompts.py` `TEMPLATE_PURPOSES` | 레이아웃 **선택** 기준 | Architect(뇌, Sonnet) |
| `backend/agents/s6/prompts.py` `SEQUENCING_RULES` | "내용이 이렇게 생겼을 때 고르라" | Architect(뇌) |
| `backend/agents/s6/prompts.py` `TEMPLATE_SPEC` | 필드명·마이크로포맷 | Writer(Haiku) |
| `web/src/lib/cardFieldSchema.ts` | 위의 프론트 미러 | 에디터 |
| `web/src/lib/imageSlots.ts` | 이미지 존 보유 여부 | 렌더러 |

**뇌 AI가 실제로 읽는 건 `prompts.py`뿐이다.** 이 문서는 그 5군데의 *상류(上流) 정본*이며,
각 레이아웃 행이 코드 어디로 전사되는지 1:1로 못박는다.

---

## 1. 컬럼 스키마 (각 레이아웃 = 한 행)

| 컬럼 | 뜻 | 전사 대상 |
|---|---|---|
| `template_type` | 코드 ID, snake_case, **불변** | `CARD_COMPONENTS` 키 (`web/src/components/cards/index.ts`) |
| 이름 | 사람용 라벨 | — |
| **선택 트리거** | "내용이 *이렇게* 생겼을 때 고른다" 한 줄 | → `SEQUENCING_RULES` / `TEMPLATE_PURPOSES` (뇌) |
| **필드 명세** | `key · shape · 필수 · 마이크로포맷` | → `TEMPLATE_SPEC` / `cardFieldSchema.ts` (Writer) |
| 수치 필드 | source 필수인 숫자 필드 (fidelity) | risk 자동판정 (CLAUDE.md §3) |
| 이미지 존 | none / 위치 | → `imageSlots.ts` |
| 상태 | 구현 단계 (아래 범례) | `CARD_COMPONENTS` 등록 여부 |

**상태 범례**
- ✅ **built** — 코드에 레지스트리·뼈대·필드스키마 전부 존재. 지금 AI가 고를 수 있음.
- 🟡 **spec / 파서재사용** — 명세만 확정. 뼈대 React 컴포넌트만 새로 만들면 됨(파서는 기존 재사용 → 저비용).
- 🔴 **spec / 신규렌더** — 명세만 확정. 차트·그래프 등 새 렌더링 코드 필요(고비용) + 수치 fidelity 부담.

**Shape 사전** (`web/src/components/cards/skin/parse.ts` — 라벨/값 내부에 `|`·`:` 금지)
- `text` — 단일 문자열. `*별표*`로 핵심어 강조.
- `pair_array` — `a:b|a:b` (2토큰). `parsePairs`.
- `stat_array` — `라벨:값:단위|...` (3토큰, 값은 숫자만). `parseStats`.
- `compare_rows` — `라벨:값:강조(0|1)|...` (3토큰). `parseCompareRows`.
- `table_rows` — `속성:A값:B값|...` (3토큰). `parseTableRows`.
- `step_array` — `단계1|단계2|...` (1토큰 리스트). split(`|`).
- `triple` — 3토큰 신규 의미(연도:제목:설명 등). **구조상 `parseTableRows` 재사용 가능**, 의미만 다름.
- `image` — 업로드 슬롯.

---

## 2. 인덱스 (DB 뷰)

| # | template_type | 이름 | 선택 트리거(요약) | 이미지존 | 상태 |
|:-:|---|---|---|:-:|:-:|
| 1 | `cover_v2` | Cover | 첫 카드 고정(표지) | zone | ✅ |
| 2 | `statement` | HookStatement | 항목화 안 되는 단일 흐름 문제/한계 | zone | ✅ |
| 3 | `feature` | CoreFeature | 항목화 안 되는 단일 흐름 혁신 설명 | zone | ✅ |
| 4 | `process_v2` | StepProcess | 순서 있는 단계 공정 3~5 | none | ✅ |
| 5 | `bigstat_compare` | BigStatCompare | 핵심 수치 1개 압도적 + 기존 대비 | none | ✅ |
| 6 | `reasons` | ReasonList | 순서없는 병렬 근거 2~4(수치 아님) | none | ✅ |
| 7 | `grid_v2` | IconGrid | 응용/항목 나열 2~4 | none | ✅ |
| 8 | `closing_v2` | ClosingCTA | 마지막 카드 고정(마무리) | zone | ✅ |
| 9 | `definition` | TermDefinition | 독자가 모를 핵심 용어 1개 | none | ✅ |
| 10 | `image_hero` | ImageHero | 인상적 그림/도식이 주인공 | zone | ✅ |
| 11 | `callout` | Callout | 한 문장 강한 강조(중앙) | none | ✅ |
| 12 | `multistat` | MultiStat | 핵심 수치 2~4개 병렬 | none | ✅ |
| 13 | `quote` | QuoteHighlight | 강한 주장/인용 한 문장 | none | ✅ |
| 14 | `compare_table` | CompareTable | 우리 vs 기존 여러 속성 비교 표 | none | ✅ |
| 15 | `radar_chart` | RadarChart | 3축 이상 다각도 성능 비교 | none | ✅ |
| 16 | `tradeoff_matrix` | TradeOffMatrix | 장점과 한계/단점이 짝으로 존재 | none | ✅ |
| 17 | `terminal_block` | TerminalBlock | 코드/프롬프트 스니펫이 핵심 | none | ✅ |
| 18 | `timeline` | EvolutionTimeline | 단계/연도별 진화 과정 | none | ✅ |
| 19 | `checklist` | ActionableChecklist | 실행 행동강령 체크리스트 | none | ✅ |
| 20 | `mythbuster` | Mythbuster | 오해 vs 진실 Q&A | none | ✅ |
| 21 | `growth_chart` | GrowthProgress | 우상향 추세(꺾은선) | none | ✅ |
| 22 | `ab_split` | ABTestSplit | A/B 둘 중 승자 증명 | none | ✅ |
| 23 | `funnel` | BottleneckFunnel | 단계별 좁아지는 퍼널/병목 | none | ✅ |
| 24 | `datapath` | MicroDatapath | 모듈·연결선 시스템 흐름 | none | ✅ |
| 25 | `tech_grid` | TechStackGrid | 활용 기술/도구 생태계 | none | ✅ |
| 26 | `decision_tree` | DecisionTree | 예/아니오 분기 의사결정 | none | ✅ |
| 27 | `ticker` | MarketTicker | 거시지표/등락 전광판 | none | ✅ |
| 28 | `do_dont` | DoThisNotThat | 행동 교정 O/X 대비 | none | ✅ |
| 29 | `swipe_bait` | SwipeBait | 다음 장 넘기기 유도(잘림 트릭) | none | ✅ |
| 30 | `chat` | ChatBubble | 대화형 메신저 메타포 | none | ✅ |

요약: **✅ 30 전부 구현완료** (2026-06-24). 차트형 5개(radar/growth/funnel + ticker/ab_split 시각화)는 SVG/도형 렌더까지 완료.
원래 분류였던 🟡(파서 재사용)·🔴(신규 렌더)는 이제 모두 빌드·시각검증 통과 — 아래 §3는 구현 메모로 유지.

---

## 3. 레이아웃 상세 (1~14: 코드에서 정확히 전사 / 15~30: 신규 설계)

### ✅ 기존 14 (현재 코드와 일치 — `prompts.py` `TEMPLATE_SPEC` 권위)

#### 1. `cover_v2` — Cover
- **트리거**: 첫 카드 고정(표지).
- **필드**: `eyebrow·text·필수`(시리즈/권호) · `headline·text·필수·*별표*`(핵심 주제, 훅) · `subtitle·text·필수`(한 줄 부제) · `org·text·필수`(기관명)
- **수치**: 없음 · **이미지존**: zone(하단 밴드)

#### 2. `statement` — HookStatement
- **트리거**: 항목화되지 않는 단일 흐름의 문제 제기/기존 한계.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*`(독자를 끄는 큰 질문) · `body·text·필수`(문제·한계 2~3문장)
- **수치**: 없음 · **이미지존**: zone(하단 밴드)

#### 3. `feature` — CoreFeature
- **트리거**: 항목화되지 않는 단일 흐름의 혁신 설명.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*`(혁신 한 줄) · `body·text·필수`(혁신 설명 2~3문장)
- **수치**: 없음 · **이미지존**: zone(우측)

#### 4. `process_v2` — StepProcess
- **트리거**: 순서가 있는 단계 공정(3~5단계).
- **필드**: `eyebrow·text·필수` · `headline·text·필수`(공정 제목) · `steps·step_array·필수`(`단계1|단계2|단계3`, 3~5) · `caption·text·선택`(보조 한 줄)
- **수치**: 없음 · **이미지존**: none

#### 5. `bigstat_compare` — BigStatCompare
- **트리거**: 핵심 수치 1개가 압도적 + 기존 대비를 보여줄 때.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `stat_value·text·필수·숫자만` · `stat_unit·text·필수` · `stat_caption·text·필수`(수치 맥락 한 줄) · `bars·compare_rows·필수`(`라벨:값:강조(0|1)`, 2~4행) · `source_ref·text·필수`(`출처: 저널(연도)·섹션`)
- **수치**: `stat_value`, `bars의 값` → **source 필수** · **이미지존**: none

#### 6. `reasons` — ReasonList
- **트리거**: 순서 없는 병렬 근거 2~4개(수치 아님).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `reasons·pair_array·필수`(`제목:본문`, 2~4)
- **수치**: 없음 · **이미지존**: none

#### 7. `grid_v2` — IconGrid
- **트리거**: 응용처/항목 나열 2~4개.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `items·pair_array·필수`(`라벨:서브`, 2~4) · `body·text·선택`(요약 한 줄)
- **수치**: 없음 · **이미지존**: none

#### 8. `closing_v2` — ClosingCTA
- **트리거**: 마지막 카드 고정(마무리·앞 카드 핵심 한 장 요약).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `body·text·필수`(마무리 2~3문장) · `source_ref·text·선택`
- **수치**: 없음 · **이미지존**: zone(하단 중앙 밴드)

#### 9. `definition` — TermDefinition
- **트리거**: 독자가 모를 핵심 용어 1개 풀이.
- **필드**: `eyebrow·text·필수`(예: "개념") · `headline·text·필수·*별표*`(용어/질문) · `body·text·필수`(중학생도 알게 2~3문장) · `caption·text·필수`(한 줄 비유·요약)
- **수치**: 없음 · **이미지존**: none

#### 10. `image_hero` — ImageHero
- **트리거**: 논문 그림/도식이 카드의 주인공일 때.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `caption·text·필수`(그림 설명 한 줄) · `image_url·image·선택`
- **수치**: 없음 · **이미지존**: zone(주역, 전체)

#### 11. `callout` — Callout
- **트리거**: 한 문장 강한 강조(중앙정렬).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*`(핵심 한 줄) · `body·text·선택`(보조 한 줄)
- **수치**: 없음 · **이미지존**: none

#### 12. `multistat` — MultiStat
- **트리거**: 핵심 수치 2~4개 병렬.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `stats·stat_array·필수`(`라벨:값:단위`, 값은 숫자만, 2~4) · `source_ref·text·선택`
- **수치**: `stats의 값` → **source 필수** · **이미지존**: none

#### 13. `quote` — QuoteHighlight
- **트리거**: 강한 주장/인용 한 문장.
- **필드**: `eyebrow·text·필수` · `quote·text·필수·*별표*가능`(큰 인용문) · `attribution·text·필수`(`— 출처/연구자`)
- **수치**: 없음 · **이미지존**: none

#### 14. `compare_table` — CompareTable
- **트리거**: 우리 vs 기존 여러 속성 비교 표.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `col_a·text·필수`(A=우리/제안) · `col_b·text·필수`(B=기존) · `rows·table_rows·필수`(`속성:A값:B값`, 2~4행) · `source_ref·text·선택`
- **수치**: `rows의 A값·B값`(숫자일 때) → source 필수 · **이미지존**: none

---

### 신규 16 (15~30) — ✅ 구현완료 (2026-06-24, 시각검증 통과)

> 모든 신규 레이아웃 공통: 첫/마지막 카드(cover_v2/closing_v2) 자리는 침범하지 않는다.
> 구현 위치: 피부 컴포넌트 `web/src/components/cards/skin/`(시각 프리미티브, 색 소유) +
> 뼈대 `web/src/components/cards/skeletons/`(배치만, 색 0). 검증 스크린샷:
> `debug_screenshots/layout_catalog/`. 아래 상태 이모지는 구현 시 비용 분류였던 기록(🟡 저비용/🔴 차트).

#### 15. `radar_chart` — RadarChart 🔴
- **트리거**: 3축 이상 다각도 성능을 한눈에 비교할 때(우리 vs 기존 다축).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `axes·triple·필수`(`축라벨:우리값:기존값`, 3~6축, 값은 숫자만) · `source_ref·text·필수`
- **수치**: `axes의 모든 값` → **축마다 source 필수**(이게 차트형의 fidelity 비용) · **이미지존**: none
- **구현 비용**: 파서는 `parseTableRows` 재사용 가능, 그러나 **SVG 레이더 렌더 신규 필요**.

#### 16. `tradeoff_matrix` — TradeOffMatrix 🟡
- **트리거**: 장점과 한계/단점이 *짝으로* 존재할 때(논문 limitation 섹션).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `pros·pair_array·필수`(`제목:본문`, 2~3) · `cons·pair_array·필수`(`제목:본문`, 2~3)
- **수치**: 없음 · **이미지존**: none · **파서**: `parsePairs` 재사용.

#### 17. `terminal_block` — TerminalBlock 🟡
- **트리거**: 코드/프롬프트/명령 스니펫이 카드의 핵심일 때(주로 CS/ML 논문).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `code·text·필수`(모노스페이스 본문, 줄바꿈 허용) · `lang·text·선택`(언어 라벨)
- **수치**: 없음 · **이미지존**: none · **파서**: `text` 재사용(렌더만 다크 터미널 스킨).

#### 18. `timeline` — EvolutionTimeline 🟡
- **트리거**: 기술/시장의 단계·연도별 진화 과정.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `events·triple·필수`(`연도:제목:설명`, 3~5)
- **수치**: 없음(연도는 라벨) · **이미지존**: none · **파서**: `parseTableRows` 재사용.

#### 19. `checklist` — ActionableChecklist 🟡
- **트리거**: 실무 적용 행동강령(체크박스형).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `items·step_array·필수`(`항목1|항목2|...`, 3~6)
- **수치**: 없음 · **이미지존**: none · **파서**: `step_array` 재사용.

#### 20. `mythbuster` — Mythbuster 🟡
- **트리거**: 흔한 오해 vs 실제(통념 깨기).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `pairs·pair_array·필수`(`오해:진실`, 2~3)
- **수치**: 없음 · **이미지존**: none · **파서**: `parsePairs` 재사용.

#### 21. `growth_chart` — GrowthProgress 🔴
- **트리거**: 우상향하는 추세/성장 지표(꺾은선).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `series·pair_array·필수`(`x라벨:y값`, y는 숫자만, 3~6점) · `source_ref·text·필수`
- **수치**: `series의 y값` → **점마다 source 필수** · **이미지존**: none
- **구현 비용**: 파서 `parsePairs` 재사용, **SVG 라인차트 렌더 신규 필요**.

#### 22. `ab_split` — ABTestSplit 🟡
- **트리거**: A/B 둘 중 하나가 이긴 것을 증명할 때(ablation/대조).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `variant_a·pair_array·필수`(`라벨:값`) · `variant_b·pair_array·필수`(`라벨:값`) · `winner·text·필수`(`a` 또는 `b`)
- **수치**: 값이 숫자면 source 필수 · **이미지존**: none · **파서**: `parsePairs` 재사용(승자는 하이라이트 렌더).

#### 23. `funnel` — BottleneckFunnel 🔴
- **트리거**: 위에서 아래로 좁아지는 단계별 퍼널/병목 분석.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `stages·stat_array·필수`(`단계:값:단위`, 위→아래, 값은 숫자만, 3~5) · `bottleneck·text·선택`(병목 단계명) · `source_ref·text·필수`
- **수치**: `stages의 값` → source 필수 · **이미지존**: none
- **구현 비용**: 파서 `parseStats` 재사용, **사다리꼴 퍼널 도형 렌더 신규**.

#### 24. `datapath` — MicroDatapath 🔴
- **트리거**: 모듈 박스 + 연결선으로 시스템 아키텍처 흐름을 보일 때.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `nodes·step_array·필수`(`노드1|노드2|...`) · `edges·pair_array·선택`(`from:to`)
- **수치**: 없음 · **이미지존**: none
- **구현 비용**: **노드-간선 그래프 레이아웃 신규**(가장 무거움). 우선순위 최하 권장.

#### 25. `tech_grid` — TechStackGrid 🟡
- **트리거**: 활용된 기술/도구 생태계 나열(로고·아이콘 타일).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `items·pair_array·필수`(`기술명:아이콘ID`, 3~6)
- **수치**: 없음 · **이미지존**: none · **파서**: `parsePairs` 재사용(아이콘은 에셋 창고에서 ID로 조회).
- **주의**: `아이콘ID`는 화이트리스트 검증 필요(없는 아이콘명 방지).

#### 26. `decision_tree` — DecisionTree 🔴
- **트리거**: 예/아니오 조건으로 갈라지는 알고리즘 의사결정.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `root·text·필수`(첫 조건) · `branches·triple·필수`(`조건:예결과:아니오결과`, 1~3)
- **수치**: 없음 · **이미지존**: none
- **구현 비용**: **분기 플로우차트 렌더 신규**.

#### 27. `ticker` — MarketTicker 🟡
- **트리거**: 거시지표/트렌드 전광판(여러 지표 + 등락).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `items·triple·필수`(`지표명:값:등락(up|down|flat)`, 3~6) · `source_ref·text·필수`
- **수치**: `items의 값` → source 필수 · **이미지존**: none · **파서**: `parseTableRows` 재사용.

#### 28. `do_dont` — DoThisNotThat 🟡
- **트리거**: 행동 교정(잘못된 예 vs 올바른 예, O/X 대비).
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `dont·pair_array·필수`(`제목:본문`, 1~3) · `do·pair_array·필수`(`제목:본문`, 1~3)
- **수치**: 없음 · **이미지존**: none · **파서**: `parsePairs` 재사용.

#### 29. `swipe_bait` — SwipeBait 🟡
- **트리거**: 다음 장으로 넘기게 유도(우측이 의도적으로 잘린 표/도식). 중간 카드 한정.
- **필드**: `eyebrow·text·필수` · `headline·text·필수·*별표*` · `teaser·text·필수`(다음 장 예고 한 줄) · `cut_items·step_array·선택`(잘려 보일 항목들)
- **수치**: 없음 · **이미지존**: none · **파서**: `step_array` 재사용(렌더에서 우측 클리핑).
- **fidelity 주의**: 정보를 *숨기는* 레이아웃이므로 잘리는 쪽에 핵심 수치/결론을 두지 않는다(다음 카드에서 반드시 공개).

#### 30. `chat` — ChatBubble 🟡
- **트리거**: 딱딱한 정보를 메신저 대화로 전달.
- **필드**: `eyebrow·text·필수` · `headline·text·선택·*별표*` · `messages·pair_array·필수`(`발화자:메시지`, 발화자는 `q`/`a` 또는 이름, 2~5)
- **수치**: 없음 · **이미지존**: none · **파서**: `parsePairs` 재사용.

---

## 4. 운영 규칙 — 레이아웃 추가/변경 시 전사 순서 (엄수)

이 문서는 정본이지만, **AI에 도달하려면 반드시 `prompts.py`까지 전사돼야 한다.** 순서:

1. **이 문서(§2 인덱스 + §3 상세)를 먼저 고친다.** `template_type`은 한번 정하면 불변.
2. **선택 트리거 → `prompts.py`**: `TEMPLATE_PURPOSES`(한 줄)와 `SEQUENCING_RULES`(내용모양 진단)에 추가. ← 뇌(Architect)가 못 고르면 죽은 행이다.
3. **필드 명세 → `prompts.py` `TEMPLATE_SPEC`** + **`web/src/lib/cardFieldSchema.ts`** 미러.
4. **shape가 신규면 → `web/src/components/cards/skin/parse.ts`에 파서 추가**(기존 재사용이면 생략).
5. **React 뼈대 작성** → `web/src/components/cards/skeletons/`, **`index.ts`의 `CARD_COMPONENTS`에 등록**.
6. **이미지 존이 있으면 → `web/src/lib/imageSlots.ts` `IMAGE_SLOT_TYPES`에 추가**.
7. **상태 컬럼을 ✅로 갱신**.

**완료 기준**: 위 2~6이 모두 끝나야 ✅. 하나라도 빠지면 🟡/🔴로 남긴다 — "문서에 썼다"는 완료가 아니다.

**fidelity 불변(CLAUDE.md §3)**: 수치 필드(`stat_array`/`compare_rows`/차트 값 등)는 레이아웃이 새 것이든 아니든 원문 source가 필수다. 차트형(🔴)은 그릴 값마다 source가 필요해 콘텐츠 파이프라인 부담이 크다는 점을 §3 상세의 "수치" 항목에 항상 표기한다.

---

## 5. Change Log

| Date | Change |
|------|--------|
| 2026-06-24 | 최초 작성. 기존 14 전사 + 신규 16 명세화(🟡 11 / 🔴 5). 7컬럼 스키마·전사 운영규칙 확정. |
| 2026-06-24 | 신규 16 **전부 구현 완료**. 피부 15개 + 뼈대 16개 신설, CARD_COMPONENTS·cardFieldSchema·prompts.py(3블록)·VALID_TEMPLATE_TYPES 전사. tsc·eslint·vitest(49)·pytest(17) 통과, 16개 시각검증(`debug_screenshots/layout_catalog/`). 전 레이아웃 ✅. |
