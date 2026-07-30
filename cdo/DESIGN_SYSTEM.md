# DESIGN_SYSTEM.md — PaperSweep 디자인 시스템

> 브랜드의 시각적 정체성. 모든 컴포넌트는 이 토큰을 참조한다.
> 코드 원본: `../web/src/app/globals.css`
> 카드 전용 토큰: `../docs/contracts/18_card_design_system.md`

---

## 브랜드 파운데이션 (변경 불가)

> **출처**: `web/src/app/globals.css :root` 직접 확인 (2026-06-26)
> 이 값들은 CDO가 창의성을 핑계로 바꿀 수 없다. 재브랜딩 시 CEO 결정 필요.

```
포인트:     포레스트 그린  --accent       oklch(38% 0.14 152)
포인트 호버:               --accent-hover oklch(32% 0.14 152)
배경 (라이트): 연백+녹빛   --bg           oklch(98% 0.005 152)
서피스:                    --surface      oklch(99.8% 0.002 152)
텍스트 주:   딥 슬레이트   --text-1       oklch(16% 0.008 152)
다크 배경:   딥 그린슬레이트 --dark-bg    oklch(14% 0.04 152)
```

토큰 사용 계층:
- `:root` — OKLCH 값 원본
- `@theme` — 반드시 `var()` 참조만 허용 (`--color-brand-500: var(--accent)`)
- 컴포넌트 — `var(--accent)` 또는 Tailwind `text-brand-500` 클래스

> hex/rgb 직접 작성 금지. `web/CLAUDE.md §6` 규칙.

**금지 목록 (CDO 재량 없음)**:
```
NEVER  화려한 그라디언트 배경 (포레스트 그린 단색 원칙)
NEVER  파스텔 톤 (신뢰감 저하)
NEVER  포인트 컬러 2개 이상 동시 사용
NEVER  애니메이션으로 텍스트 등장 (가독성 방해)
NEVER  배경 이미지 위 저대비 텍스트
NEVER  @theme에 hex 직접 작성
```

**미적 방향**: 라이트 모드 기반 · 포레스트 그린 포인트 · 데이터 중심
- 흰 배경에 진한 녹색 포인트 — 신뢰감·전문성 (연구자 타겟)
- 데이터(논문 수치, 카드 내용)가 주인공
- 다크 모드는 auth/CTA 구역 한정 (`--dark-bg` 사용)

---

## 컬러 시스템

토큰은 OKLCH로 정의, `globals.css`의 `:root`에 위치.
`@theme` 블록은 반드시 `var()` 참조만 허용.

### 앱 크롬 토큰 (`--*`)

| 토큰 | 역할 | 사용처 |
|------|------|--------|
| `--accent` | 브랜드 포인트 컬러 | CTA, 활성 상태, 링크 |
| `--accent-hover` | hover 상태 | 버튼 hover |
| `--bg` | 앱 배경 | body |
| `--bg-subtle` | 패널 배경 | 사이드바, 카드 컨테이너 |
| `--surface` | 컴포넌트 표면 | 카드, 드롭다운 |
| `--border` | 경계선 | divider, input border |
| `--text-1` | 주요 텍스트 | 제목, 본문 |
| `--text-2` | 보조 텍스트 | 레이블, 메타 |
| `--text-3` | 비활성 텍스트 | placeholder, disabled |

### 카드 토큰 (`--set-*`)

카드 내부 렌더에만 사용. 앱 크롬과 네임스페이스 분리.

| 토큰 | 역할 |
|------|------|
| `--set-bg` | 카드 배경 |
| `--set-accent` | 카드 강조 색 |
| `--set-text-headline` | 카드 헤드라인 텍스트 색 |
| `--set-text-body` | 카드 본문 텍스트 색 |
| `--set-badge-bg` | 배지 배경 |

> `--*` (앱 크롬) ↔ `--set-*` (카드) 혼용 금지.

---

## 타이포그래피

```css
--font-sans: 'Pretendard', system-ui, sans-serif;   /* 한국어 + UI */
--font-mono: 'JetBrains Mono', monospace;            /* 코드, 수치 */
```

### 스케일

| 레벨 | 크기 | 용도 |
|------|------|------|
| Display | 2.5rem / 700 | 랜딩 히어로 |
| H1 | 1.75rem / 700 | 페이지 제목 |
| H2 | 1.25rem / 600 | 섹션 제목 |
| Body | 1rem / 400 | 본문 |
| Small | 0.875rem / 400 | 메타, 레이블 |
| Mono | 0.875rem / 400 | 수치, 코드 |

---

## 간격 시스템 (8px 기반)

```
4px   — 극소 간격 (아이콘-텍스트)
8px   — 소 (컴포넌트 내부 패딩)
16px  — 중 (카드 패딩, 섹션 내부)
24px  — 대 (섹션 간 구분)
32px  — 특대 (페이지 레벨)
```

---

## 상태 컬러

| 상태 | 의미 | 사용처 |
|------|------|--------|
| `--status-critical` | CRITICAL 리스크 | S6 리스크 배지 |
| `--status-high` | HIGH 리스크 | S6 리스크 배지 |
| `--status-medium` | MEDIUM | 경고 |
| `--status-low` | LOW / 정상 | 정상 상태 |
| `--status-success` | 완료 | 발행 완료 |

---

## 브랜드 마크

- 로고: 텍스트 기반 (`PaperSweep`), 좌상단 고정
- 카드 내 워터마크: **없음** (불필요한 기능으로 제거 결정, 2026-06-26)
