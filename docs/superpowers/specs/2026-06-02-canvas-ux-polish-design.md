# Canvas UX Polish — Design Spec
> 2026-06-02 | Phase 3 잔여 작업

## Problem

빅뱅 마이그레이션(iframe → React 캔버스) 이후 기능은 동작하지만 3가지 UX 문제가 남아있다.

1. 캔버스 텍스트가 편집 가능한지 사용자가 알 수 없음 (hover 피드백 없음)
2. focused outline이 미정의 CSS 토큰(`--theme-primary`)을 참조해 동작 불안정
3. Topbar의 `saveState` prop이 전달되지만 실제로 사용되지 않음 — 클라우드 아이콘이 항상 빨간 점
4. LeftPanel 카드 추가 버튼이 동작 없는 placeholder 상태

## Decision

### 1. EditableText — hover 힌트 (A안 확정)

edit 모드에서만 적용. render/thumbnail 모드는 영향 없음.

```
hover: background rgba(22,163,74,0.08), border-radius 4px, cursor text
```

구현 위치: `EditableText.tsx` — inline style에 `onMouseEnter/onMouseLeave` 핸들러 추가.
단, `focused === true`일 때는 hover 스타일 무시 (outline이 우선).

### 2. EditableText — focused outline 토큰 수정

현재: `var(--theme-primary)` — globals.css에 미정의.
수정: `var(--brand)` — 이미 정의된 토큰. `1.5px solid` 유지, `outlineOffset: 4px` 유지.

### 3. Topbar — saveState 연결

`saveState` prop을 Topbar의 destructured props에 추가하고 클라우드 아이콘 dot에 연결.

| saveState | dot 색상 | 부가 효과 |
|-----------|---------|---------|
| `saved`   | `#16A34A` (초록) | 없음 |
| `saving`  | `#D97706` (주황) | 클라우드 아이콘 pulse 애니메이션 |
| `idle`    | `#D97706` (주황) | 없음 (로컬 변경 있음, auto-save 대기) |
| `error`   | `#DC2626` (빨강) | 현재 상태 유지 |

pulse 애니메이션: `@keyframes pulse { 0%,100% { opacity:1 } 50% { opacity:0.4 } }`, 1s infinite.

### 4. LeftPanel — 카드 추가 버튼 disabled

- `disabled` 속성 추가
- `title="준비 중"` tooltip
- opacity 0.4, cursor not-allowed
- onClick 핸들러 없음

## Out of Scope

- 카드 삭제 기능 (별도 작업)
- 카드 순서 변경 (별도 작업)
- AI 카드 추가 / 장수 추천 (미래 기능)

## Files Changed

| 파일 | 변경 |
|------|------|
| `web/src/components/cards/shared/EditableText.tsx` | hover 핸들러, outline 토큰 수정 |
| `web/src/components/editor/Topbar.tsx` | saveState prop 연결, dot 색상/animation |
| `web/src/components/editor/LeftPanel.tsx` | add 버튼 disabled |

## Success Criteria

- 처음 보는 사람이 카드 위에 마우스를 올리면 텍스트가 편집 가능함을 알 수 있다
- 저장 중일 때 Topbar 클라우드 아이콘이 pulse된다
- 저장 완료 시 초록 점으로 전환된다
- 카드 추가 버튼이 비활성화 상태로 표시된다
