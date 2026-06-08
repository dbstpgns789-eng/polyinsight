# 18 · 카드 디자인 시스템 (skin / skeleton)

> v1.0 | 2026-06-08
> 카드뉴스 렌더의 단일 진실. 코드: `web/src/components/cards/`.
> 배경/근거: `docs/superpowers/specs/2026-06-05-카드-디자인-시스템-design.md`,
> 이미지: `docs/superpowers/specs/2026-06-07-이미지-통합-심화-v2-design.md`.

---

## 1. 왜 이 구조인가 (Problem)

초기 카드는 템플릿마다 자기 배경·색·폰트·박스를 직접 정의하는 **"섬(island)"** 이었다.
그 결과 한 세트의 카드들이 서로 다른 카드뉴스처럼 보였고("검정→흰→갈색 불일치"),
독자가 "안 읽힌다"고 했다. 근본 원인은 손재주가 아니라 **공유 디자인 시스템의 부재**.

→ 2026-06-05 섬 구조를 **피부(skin) / 뼈대(skeleton) 분리**로 재설계.
2026-06-08 구 섬 12개 전량 철거, 신 8뼈대 단일 체계로 확정.

## 2. 핵심 분리

| 층 | 역할 | 변하나? |
|---|---|---|
| **피부 (skin = SET)** | 배경 톤 + 3색 토큰 + 타이포 위계 + 공유 컴포넌트 라이브러리 + 여백 리듬 | 세트당 한 번 정의(고정) |
| **뼈대 (skeleton = LAYOUT)** | 슬롯 배치만 (1단 히어로·2단 비교·목록·큰 수치 등) | 내용 모양에 따라 S6/유저 선택 |

### 🔒 강제 규칙 (코드로 강제)

> **뼈대 컴포넌트는 색·배경·폰트·border를 절대 정의하지 못한다.**
> 오직 세트가 준 토큰·피부 컴포넌트만 조립한다. 스타일을 가진 primitive는 피부 컴포넌트뿐.

레이아웃이 달라도 한 시리즈로 보이는 것을 보장. 검증: 뼈대 파일에
`background`/`color:`/`fontSize`/`border*` grep 0건 (CI 게이트 아니지만 PR마다 확인).
새 세트 추가 = 토큰 값만 교체, 뼈대·컴포넌트 무변경.

## 3. 토큰 (`--set-*`) — `web/src/components/cards/skin/sets.ts`

앱-크롬 토큰(`globals.css :root` OKLCH)과 **분리된 네임스페이스**. CardFrame이 inner style로 주입.

```
색(3색 규율): --set-bg · --set-bg-grad · --set-bg-gradient · --set-accent · --set-accent-ink
              --set-ink-strong · --set-ink-muted · --set-ink-faint · --set-surface · --set-surface-border
타이포(1080 절대 px): --set-display · --set-headline · --set-subhead · --set-body · --set-caption · --set-eyebrow
간격/모양: --set-pad · --set-gap · --set-radius-box · --set-radius-pill · --set-font
```

**세트(현재 2개):**
- `EDITORIAL_LIGHT_SET` — **기본**. 밝은 종이(OKLCH hue152) + 진한 포레스트 + 굵은 타이포.
  미감 방향 C(에디토리얼 라이트), 앱 'Academic Desk'와 통일. `#000`/`#fff` 금지(OKLCH).
- `DEEP_TEAL_SET` — 딥틸(#0E5E60) + 골드. 첫 세트(현재 비기본).

> 규율: `@theme`/토큰에 hex 직접 금지는 앱-크롬 규칙(`web/CLAUDE.md §6`). `--set-*`는
> 카드 전용 독립 네임스페이스라 세트 정의 파일에서 OKLCH/hex 리터럴을 직접 가진다(여기가 단일 출처).

## 4. 8 뼈대 — `skeletons/`

서사 아키타입(실험형 9 beat)을 생김새로 압축한 8개. 5장=압축, 7장=표준으로 부분집합 사용.

| # | 뼈대 (`template_type`) | beat / 용도 | 이미지 |
|---|---|---|---|
| 1 | `cover_v2` (Cover) | 표지 | 존(하단 밴드) |
| 2 | `statement` (Statement) | 훅·기존 한계 | 존(하단 밴드) |
| 3 | `feature` (Feature) | 핵심 혁신 | 존(우측) |
| 4 | `process_v2` (Process) | 제작 3스텝 | 없음 |
| 5 | `bigstat_compare` (BigStatCompare) | 성능 수치 + vs 기존 + 출처 | 없음 |
| 6 | `reasons` (Reasons) | 왜 이 소재(세로 근거) | 없음 |
| 7 | `grid_v2` (Grid) | 응용처(아이콘 격자) | 없음 |
| 8 | `closing_v2` (Closing) | 마무리·협력 | 존(하단 중앙 밴드) |

레지스트리 `cards/index.ts`의 `CARD_COMPONENTS`가 `template_type → 컴포넌트` dispatch.

## 5. 피부 컴포넌트 라이브러리 — `skin/` (16개)

스타일을 가진 유일한 primitive. 뼈대는 이것만 조립한다.

- **텍스트(5)**: `Eyebrow` · `Headline`(핵심어 `*em*`) · `Subhead` · `Body` · `Caption`
- **컨테이너/마크(5)**: `CardSurface` · `BgMotif` · `BrandMark` · `AccentDivider` · `IconChip`
- **복합/특수(5)**: `SourceTag` · `StepFlow` · `BigStat` · `CompareBars` · `FeatureColumn`
- **이미지(1)**: `VisualZone` (§6)

> 우리만 필요한 것(상용 코인 템플릿엔 없음) = `SourceTag` · `VisualZone` · `BigStat` — fidelity 정체성의 증거.
> 보류(어느 뼈대도 안 씀, YAGNI): Pill · TintedBox · LabeledRow — 미구현.

### 필드 포맷 (S6 출력 ↔ 프론트 파서 계약, `shared/delimiters.ts`)
- `headline`: `*강조*` 마커로 핵심어 em
- `bars` (CompareBars): `label:value:isPrimary` 를 `|`로 나열
- `steps` (StepFlow): `|` 구분
- `reasons` / `items`: `title:body`(또는 `label:sub`) 를 `|`로 나열

## 6. 이미지 — 모델 A "디자인된 역할 고정"

이미지는 뼈대 설계의 일부다. **고정된 존에만** 들어가고, 사용자는 "올릴까 말까"만 판단한다
(업로드만 — AI 생성 금지 = fidelity). 상세: `docs/.../2026-06-07-이미지-통합-심화-v2-design.md`.

- **담긴 존 원칙**: 이미지는 항상 둥근 프레임(`VisualZone`) 안에 담기고 **텍스트는 사진 위에 절대 겹치지 않는다** → readability 보호. 배경 풀블리드 금지.
- **무이미지 적응**: `showImage = !!image_url || mode==='edit'`. 이미지 없으면 텍스트가 자리를 채움(빈 박스 0). 에디터에선 점선 드롭존만.
- **focal(초점)**: `Card.focal{x,y}`(0~1). 편집 모드 이미지 본문 클릭 = 초점 설정(cover 크롭 위치). 우상단 ↻ = 교체. `web/src/lib/focal.ts`.
- **image_fit(맞춤)**: `Card.image_fit: 'cover'|'contain'`(기본 cover). 좌상단 토글. **contain = 이미지 통째로(잘림 0)** — 도식·그래프에 적합, 외부 사전편집 불필요. focal은 cover에서만 의미.

## 7. 렌더 경로

에디터 미리보기와 export PNG가 **같은 React 컴포넌트(단일 소스)** 에서 나온다.

```
CardRenderer(card, mode) → CardFrame(--set-* 주입) → 뼈대 → 피부 컴포넌트 조립
mode = 'edit'(에디터) | 'render'(S7) | 'thumbnail'(좌패널)
```

S7 PNG = Playwright가 `/render/{job}/{card}` 라우트를 `goto`(`mode="render"`) → 스크린샷.
(과거 Jinja 경로는 2026-06-08 제거. `docs/05_agent_design.md` §6-2/§10 참조.)

## 8. 새 세트 추가하는 법

1. `skin/sets.ts`에 `CardSet` 하나 더 정의 — 씨앗색만 갈아끼움(토큰 값만).
2. 뼈대·피부 컴포넌트·레이아웃 **무변경**(강제 규칙이 보장).
3. CardFrame `set` prop으로 주입 / 세트 선택 UI로 전환(멀티세트는 후속 P3).

## 9. 관련 문서

- 데이터 모델(CardSlot·focal·image_fit): `docs/07_api_data_model.md`
- S7 렌더(React goto): `docs/05_agent_design.md` §6
- 에디터 화면/편집권한: `docs/12_card_editor_content.md`
- 미감 결정·서사 아키타입: `docs/superpowers/specs/2026-06-05·06-07-*`
