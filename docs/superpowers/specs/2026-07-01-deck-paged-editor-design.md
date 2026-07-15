# 덱 편집기 한 장씩 페이징 뷰 (Phase 3f) 설계

> 2026-07-01 · 편집 모드에서 덱을 긴 스크롤 대신 **한 카드씩 페이징**으로 표시.
> 레거시 에디터의 단일 카드 뷰 감성을, 단일 저작 HTML 문서를 유지한 채 재현.

## Context

편집 모드(`DeckEditor`)는 저작 HTML(카드 7장이 세로로 쌓인 한 문서)을 iframe에 통째로
마운트해 **긴 스크롤**로 보여준다. 사용자는 한 장씩 중앙에 띄우고 페이징으로 넘기는 뷰를
원한다(비전문가 관찰: "쭉 보여주기의 한계"). 핵심 제약: 덱은 **HTML 한 문서**여야 한다 —
그래야 `serialize`가 전체 클린 HTML을 뽑아 **수치검증(해자)+PNG 재렌더**가 성립하고, 선택·
다중선택·정렬·undo가 한 DOM 위에서 작동한다. 따라서 카드별 iframe 분할은 금지(계약 파괴).

확정 결정(사용자, 시각적 선택):
1. **선택 연동 ON** — 편집 중인 카드가 항상 화면에 보인다(페이징에 내재).
2. **편집 모드만 페이징** — 보기 모드(PNG 7장 피드)는 지금처럼 스크롤 유지.
3. **페이징 통일** — "쭉 보기" 토글 버튼 없음(상단바 깔끔).

## 접근 (문서 유지 + 비활성 카드 숨김)

스크롤 좌표 계산 대신 **비활성 카드를 시각적으로 숨긴다**. 활성 카드 1장만 렌더되면 기존
`HEIGHT` 메시지가 iframe을 그 한 장 크기로 자동 리사이즈한다(추가 사이징 로직 최소).

- 에이전트에 `pi-hidden` 클래스 + 아티팩트 스타일시트(`<style data-pi-artifact>.pi-hidden{display:none!important}`)
  주입. 활성 카드 외 전부 `pi-hidden`.
- `display:none` 자식은 flex 레이아웃에서 완전 제외 → gap도 사라져 한 장만 깔끔히 남는다.
- **직렬화 안전**: serialize 시 클론에서 아티팩트 스타일 제거(기존 `[data-pi-artifact]`) +
  모든 요소에서 `pi-hidden` 클래스 제거 → 저장 HTML엔 7장 전부 온전(숨김 흔적 0).

## 동작 사양

### 1. 페이징 상태
- `paged` 모드는 **편집 모드에서만** 활성(`setMode('edit')` 시 진입, `'view'` 시 해제하고 전부 표시).
- `activeCard`(0-based) 상태. 에이전트가 카드 목록(`[data-screen-label]`)을 사실 소스로 보유.
- 진입 시 `activeCard=0`(1번 카드).

### 2. 페이지 이동
- 부모→에이전트 `SET_PAGE {index}` → 해당 카드만 표시(나머지 `pi-hidden`) + **선택 해제**(숨은
  요소의 유령 오버레이 방지) + `PAGE {index,count}` 통보.
- 경계 클램프(0 ≤ index < count).

### 3. 선택 연동(내재)
- 페이징 모드에선 활성 카드만 보이므로 클릭·마퀴·shift는 **항상 현재 카드 안**(D2 카드경계 불변식과
  정합) → "편집 중인 카드가 항상 보인다"가 구조적으로 보장.
- 에이전트는 `SELECTED` 시 요소의 카드 index를 함께 계산해 필요하면 `PAGE`로 부모 n/N 동기화
  (현재는 항상 현재 페이지 = 무해). **미래 확장**: 충실성 패널의 수치 클릭 → 해당 카드로 점프 가능.

### 4. 메시지 프로토콜 확장
- 부모→에이전트: `SET_PAGE {index}`.
- 에이전트→부모: `PAGE {index, count}` (진입·이동 시). count로 부모 페이징 UI 구성.

### 5. 부모 UI (page.tsx, 편집 모드에서만)
- 카드 영역 상단/하단에 `‹  n / N  ›` 페이저(이전·다음, 양끝 비활성).
- 키보드 ←/→ 페이지(단, 텍스트 편집 중=contenteditable 포커스 시 캐럿 이동 우선 → 페이징 무시).
- 저장·undo/redo·편집종료 상단바는 그대로.

### 6. 비목표
- 보기 모드 페이징(결정 2), "쭉 보기" 토글(결정 3), 카드 썸네일 레일(후속 여지), 카드 추가/삭제 UI.

## 직렬화·검증·백엔드
- **백엔드 무변경.** `serialize`가 `pi-hidden` 클래스·아티팩트 스타일을 제거해 저장 HTML은
  7장 온전 → 기존 `PATCH /api/deck/{id}` + 재검증 + `render_deck` 그대로. `data-screen-label` 7 유지.

## 구현 리스크 & 대응
| # | 리스크 | 대응 |
|---|---|---|
| R1 | 숨김이 저장 HTML에 누수 | serialize에서 `pi-hidden` 클래스 제거 + 아티팩트 스타일 제거(공통마커) |
| R2 | 진입 초기 전체높이 → 한장으로 줄며 깜빡 | `setMode('edit')`에서 즉시 숨김 적용 후 HEIGHT 발화 |
| R3 | 페이지 이동 시 이전 선택의 유령 오버레이 | SET_PAGE에서 deselect |
| R4 | 화살표키와 텍스트 캐럿 충돌 | contenteditable 포커스 시 페이징 키 무시 |
| R5 | 보기↔편집 전환 시 숨김 잔존 | `setMode('view')`에서 pi-hidden 전부 제거 |

## 구현 슬라이스 (각 후 tsc+eslint + 하네스)
- **3f-1 에이전트**: paged 상태 + `pi-hidden`/아티팩트 스타일 + `SET_PAGE`/`PAGE` + serialize 정리 + setMode 연동.
- **3f-2 부모 배선**: `DeckEditorHandle.setPage`, `PAGE` 라우팅, page.tsx 페이저 UI + 상태 + 화살표키.

## 검증 (하네스, localhost)
1. 편집 진입 → 카드 1장만 표시(나머지 `display:none`), HEIGHT가 한 장 크기.
2. `SET_PAGE 1` → 2번 카드만 표시, `PAGE{index:1,count}` 수신, 이전 선택 해제.
3. 페이지 내 요소 클릭/드래그/정렬 정상.
4. serialize → `pi-hidden`/`data-pi-*` 잔재 0, `data-screen-label` 전부 유지.
5. `setMode('view')` → 전 카드 표시 복원.
6. (풀스택 1회) 페이징 편집 후 저장 PATCH 200 + 7장 PNG 재렌더.

## 변경 파일
- `web/src/components/deck/editorAgent.ts` — paged/pi-hidden/SET_PAGE/PAGE/serialize 정리.
- `web/src/components/deck/DeckEditor.tsx` — `setPage` 핸들 + `PAGE` 콜백 라우팅.
- `web/src/app/deck/[jobId]/page.tsx` — 페이저 UI·상태·화살표키(편집 모드 한정).
