# 덱 다중선택 + 정렬/분배 + 수치입력 (Phase 3e) 설계

> 2026-07-01 · 로드맵 #1(다중선택) + #2 일부(정렬·분배) + Figma식 수치 X/Y·W/H 입력.
> Phase 3d(직접조작)의 연장 — 기존 모듈을 재작성 없이 늘린다.
> **핵심 불변식: 사용자의 모든 조작은 예외 없이 하나의 undo 스택에 쌓이고, 어느 상황(타이핑 중·다중선택 중 포함)에서도 Ctrl+Z/버튼으로 순차 복원된다.**

## Context

헌법 v3.0에서 덱은 AI가 저작한 자유 HTML 한 덩어리이고, Phase 3d에서 마우스 직접조작(단일 요소
드래그·리사이즈·스냅·undo)을 붙였다. 그러나 **한 번에 하나만** 다룰 수 있어, 여러 블록을 함께
옮기거나 가지런히 정렬하는 실제 편집 흐름이 막혀 있다. 사용자가 산출물을 Figma로 빼가면 제품
실패다(편집은 우리 안에서 완결돼야 한다). 이 작업은 그 완결성의 다음 조각: **다중선택 → 함께 이동
→ 정렬·분배 → 수치 정밀 입력**. 스펙 3d(`2026-06-30-deck-direct-manipulation-design.md`)의 로드맵
표에서 #1은 #2·#4의 전제로 예약돼 있고, history는 이미 커맨드 패턴이라 `CompositeCommand`로 흡수만
하면 된다(재작성 0).

확정 범위(브레인스토밍 결과):
- 조작: **선택 + 이동 + 정렬(#2 일부)**
- 선택 방법: **Shift클릭 + 마퀴 드래그**
- 정렬 기준: **선택집합 바운딩박스**(Figma 기본)
- 구현 상한: **정렬 행 + 수치 X/Y·W/H 입력** (레이어패널·회전·그룹은 이번 범위 밖)
- **되돌리기 보편성**을 명시적 불변식으로 요구

## 비목표 (이번 슬라이스 제외 — 범위 방어)

그룹화(#4)·**다중 리사이즈/그룹 스케일**·회전(#5)·레이어 패널(#3)·**교차 카드 선택**·협업/실시간.

---

## 아키텍처 결정

**D1. 선택 표현: `sel`(단일) → `selection[]`(배열).** Set 대신 배열 — 분배의 순서 계산과
직렬화 안정성에 유리. `primary()` = `selection[selection.length-1]`(마지막 클릭). 텍스트 인라인
편집·리사이즈·스타일·삭제·순서·흐름복귀 같은 **단일 전용 조작은 `selection.length===1`일 때만** 활성.
이동·정렬·분배·수치는 집합 전체.

**D2. 카드 경계 불변식: 한 선택집합은 반드시 한 카드 안.** 각 카드가 독립 좌표계(1080×1350)라
카드를 넘는 정렬/이동은 좌표 혼선(버그). 다른 카드 요소를 클릭/Shift클릭/마퀴하면 그 카드로 선택
리셋. `sameCardGuard(el)`로 강제.

**D3. 기하 대상 정규화: 이동/정렬/분배/수치는 "카드의 직계 자식"에 대해 수행.** 클릭은 리터럴
요소(중첩 텍스트 편집 위해)를 고르되, 기하 연산 대상은 `cardChild(el)`(카드 직계 자식 조상)로 승격.
이유: `position:absolute`는 가장 가까운 positioned 조상 기준이라 중첩 요소를 승격하면 좌표가 카드가
아닌 래퍼 기준이 됨 → 좌표 붕괴. 마퀴도 직계 자식만 후보(스냅의 `siblingsOf` 입도와 일치).

**D4. 백엔드 무변경.** 정렬/이동/수치 = 기존 드래그처럼 인라인 `left/top/width/height`만 생성.
기존 `PATCH /api/deck/{job_id}` + `persist_edited_deck`(재검증+`render_deck`) 그대로. 신규
엔드포인트·DB·계약 변경 없음. `data-screen-label` 7개 불변.

---

## 동작 사양

### 1. 선택 모델 (`editorAgent` selection 모듈 개편)
- `var sel = null` → `var selection = []`. 헬퍼: `primary()`, `inSelection(el)`, `addSel/removeSel/setSel/clearSel`.
- `refreshEditable()`: 선택 변경 후 매번 호출 — `selection.length===1 && isTextLeaf(primary())`면 그
  요소만 contenteditable, 아니면 모든 요소 contenteditable 제거. (1→2 전환 시 첫 요소 편집 해제)
- **오버레이 풀**: 선택 요소마다 얇은 아웃라인(모두 아티팩트 마커). 2개+면 **집합 바운딩박스**(점선) 추가.
  `ensureOverlays(n)`로 풀 재사용(초과분 숨김), `positionOverlays()`가 전원 재배치.

### 2. 인터랙션
- **클릭**: 단일 선택(기존). 텍스트면 편집.
- **Shift/Ctrl+클릭**: `inSelection`이면 제거, 아니면 추가. 다른 카드면 setSel로 리셋.
- **마퀴 드래그**: `pick`이 null인 빈 영역 mousedown → 임계 초과 시 분홍 점선 사각형(아티팩트).
  mouseup에 시작 카드의 직계 자식 중 교차하는 것 일괄 선택. 임계 미만이면 기존대로 deselect.
  (기존 `onMouseDown`의 "빈영역=즉시 deselect"를 "마퀴 시작"으로 교체)
- **다중 드래그 이동**: 2개+ 선택 상태로 요소 드래그 → 아래 "다중 이동 순서(R2)"대로 전원 이동, 하나의
  `compositeCmd`. 스냅은 집합 바운딩박스 기준(가장자리/중심 → 카드 가이드).

### 3. 오버레이 & 핸들
- 8방향 리사이즈 핸들은 **정확히 1개 선택일 때만** 노출(다중 스케일은 범위 밖). `positionOverlays`가
  `selection.length===1 && mode==='edit'`에서만 핸들 표시.

### 4. 정렬·분배 + 수치 (DeckElementPanel 확장)
- **정렬 6버튼**(가로 좌/중/우, 세로 상/중/하): 2개+에서 활성. 집합 바운딩박스 기준. 각 대상 absolute
  승격 후 좌표 지정, 하나의 compositeCmd.
- **분배 2버튼**(가로/세로 균등): 3개+에서 활성. 알고리즘 = **인접 요소 간 간격(edge-to-edge)을 균등화**,
  양 끝 고정. 정렬축 좌표로 정렬 후 총여백을 (n-1) 등분.
- **수치 X/Y·W/H**:
  - 단일: X/Y=left/top(편집 시 absolute 승격), W/H=width/height.
  - 다중: X/Y=집합 바운딩박스 좌상단(편집 시 전체 이동 = delta). **W/H는 읽기전용("혼합됨" 또는 집합
    크기 표기)** — 그룹 스케일 범위 밖.
  - 입력 UX: **로컬 상태 + Enter/blur에 커밋**(키 입력마다 postMessage 금지 → 잰크·DIRTY 폭주 방지).
    선택 변경 시 로컬값 동기화. DeckElementPanel의 color `defaultValue` 패턴과 동형.

### 5. 되돌리기 보편성 (신규 불변식 — 구멍 메움)
- 단일 스택·단일 진입점: Ctrl+Z / Ctrl+Shift+Z(/Ctrl+Y) / ↶↷ 버튼 → 전부 `undo()/redo()` 하나로(유지).
- **현재 유일한 미포착 조작 = 텍스트 타이핑**(contenteditable 네이티브라 스택에 안 오름 → 타이핑 중
  Ctrl+Z가 직전 레이아웃 커맨드를 취소하는 어긋남). **수정**: 텍스트 요소가 **커밋될 때(blur/선택 변경/
  드래그 시작)** `textCmd(el, before→after textContent)`를 스택에 푸시. `focusin` 시 before 스냅샷,
  커밋 시점에 after와 다르면 push.
- 신규 조작 전부 커맨드화: 다중이동=compositeCmd, 정렬/분배=compositeCmd, 수치=layoutCmd/composite.
- `compositeCmd(cmds)` = `run: 정방향 forEach`, `undo: 역순 forEach`. 기존 undoStack 그대로 흡수.
- undo/redo 후 **detach된 선택 요소 정리**: 기존 `document.body.contains(sel)` 검사를 selection 배열
  필터로 확장(undo로 삭제 복원/재삭제 시 dangling 방지).

### 6. 메시지 프로토콜 확장
- 부모→에이전트 신규: `ALIGN {axis:'left'|'hcenter'|'right'|'top'|'vcenter'|'bottom'}`,
  `DISTRIBUTE {axis:'h'|'v'}`, `SET_RECT {left?,top?,width?,height?}`(선택 대상에 적용).
- 에이전트→부모: `SELECTED` 확장 — `count`, `rect{x,y,w,h}`(자연 카드좌표; 단일=요소, 다중=집합박스),
  `mixed`(W/H 혼합 여부), `canDistribute`(count>=3). count>1이면 `tag='(다중 N)'`, `editable=false`,
  `styles`=primary 기준.

### 7. 직렬화 (아티팩트 누수 원천봉쇄)
- **모든 주입 요소에 공통 마커 `data-pi-artifact` 부여**(오버레이·핸들·가이드·마퀴·집합박스). serialize를
  `[data-pi-artifact]` 한 셀렉터로 제거하도록 리팩터 → 신규 아티팩트 추가 시 serialize 갱신을 잊어도
  누수 없음(기존은 종류마다 셀렉터 나열 → 잊으면 저장 HTML 오염). 기존 개별 속성은 로직용으로 유지.
- contenteditable 제거는 기존 유지. 결과 HTML은 인라인 스타일만 늘 뿐 계약 유지.

---

## 이전 대규모 작업 교훈 (반드시 선반영)

1. **`editorAgent`는 템플릿 문자열 주입 ES5 스크립트 → tsc 미검사.** 내부 버그는 런타임에만 노출.
   → 함수 잘게, 슬라이스마다 Playwright 런타임 드라이브. `var`/`function` 유지(arrow/const/클래스 금지).
2. **백틱·`${` 절대 금지** (외부 템플릿 리터럴과 충돌). 문자열은 `'...'`, 개행은 `\\n`(이중 이스케이프).
3. **next dev(turbopack) 불안정**: editorAgent가 더 커지면 HMR 재컴파일에서 간헐 500/워커크래시.
   → 에이전트 변경 후 next dev **재시작(fresh)**. Playwright `goto(wait_until='commit')` + `window.__piAgent`
   대기로 타이밍 안정화.
4. **Next 16은 `127.0.0.1` dev 리소스 차단** → 브라우저 검증은 반드시 `localhost:3000`.
5. **dev DB는 uvicorn 시작 시에만 migrate()**. 백엔드 무변경이라 스키마 리스크는 없지만 seed 시 paper_text
   컬럼 존재 확인.
6. **테스트 하네스 소실**: `scratchpad/seed_deck.py`(demo 계정+덱)·`drive_dm.py`(합성 마우스 이벤트로 iframe
   내부 자연좌표 조작)가 강제종료로 사라짐 → **재작성 필요**. drive_dm에 다중선택(shift+click 합성)·마퀴
   드래그·정렬 클릭 시나리오 추가.
7. **좌표는 iframe 내부 자연좌표**(부모 scale 무관) — 3d에서 검증됨. 마퀴·다중이동도 동일 전제 재사용.

## 구현 리스크 & 대응 (예상 버그 사전 차단)

| # | 리스크 | 증상 | 대응 |
|---|---|---|---|
| R1 | `sel` 참조가 다수 함수에 산재 | 배열 전환 시 stale 단일 가정·런타임 오류 | `primary()`로 일괄 치환, 단일전용 조작은 length 게이트 |
| R2 | **promote 순서 버그** | 흐름 요소를 하나 absolute 승격→나머지 리플로우→base좌표 오염 | **전원 rect를 먼저 캡처 → 그 다음 전원 promote → 캡처값으로 left/top 지정** |
| R3 | 중첩 요소 absolute 승격 | offsetParent가 카드 아닌 래퍼 → 좌표 붕괴 | D3: 기하 대상은 `cardChild(el)` 직계 자식으로 정규화 |
| R4 | 아티팩트 누수 | 마퀴/집합박스가 저장 HTML에 잔존 → 계약 오염 | D7: 공통 `data-pi-artifact` 마커 + 단일 셀렉터 제거 |
| R5 | 1→다중 전환 시 contenteditable 잔존 | 편집 커서가 여러 곳/이상동작 | `refreshEditable()` 매 선택변경 호출 |
| R6 | 수치 입력 controlled 라운드트립 | 키 입력마다 postMessage → 잰크·커서 튐 | 로컬 상태 + Enter/blur 커밋, 선택변경 시 동기화 |
| R7 | 텍스트 타이핑 미포착 undo | 타이핑 중 Ctrl+Z가 레이아웃 취소 | §5 textCmd(커밋 시 push) |
| R8 | undo로 삭제복원/재삭제 시 dangling 선택 | undo 후 오류/유령 오버레이 | selection 배열에서 detach 요소 필터 |
| R9 | 마퀴 vs 드래그이동 오인 | 빈영역 클릭이 이동으로, 요소 클릭이 마퀴로 | mousedown 타깃 `pick` 결과로 분기 + 임계 |
| R10 | 마퀴 교차판정 좌표계 | scale·scroll로 오선택 | getBoundingClientRect(둘 다 iframe 뷰포트 좌표) 교차, 시작 카드 한정 |
| R11 | 분배 n<3 | 0분모/NaN | count>=3 게이트 + canDistribute |
| R12 | 정렬 대상 flow 요소 | left/top 무효 | 정렬 커맨드가 promote 포함(before=flow, after=absolute), R2 순서 준수 |
| R13 | SELECTED 페이로드 변경 | 소비자(패널) 타입 불일치 | 신규 필드 optional, tsc로 확인 |

## 구현 슬라이스 (각 슬라이스 후 tsc+eslint + Playwright 런타임 드라이브)

- **3e-0 하네스 재건**: `seed_deck.py`·`drive_dm.py` 재작성(+shift/marquee/정렬 합성). 3d 회귀 1회 확인.
- **3e-1 선택 모델**: `selection[]` + primary/refreshEditable + 오버레이 풀 + 집합 바운딩박스 +
  serialize 공통마커 리팩터. **아직 다중조작 없음**(단일 회귀 무손상 우선).
- **3e-2 다중선택 입력**: Shift/Ctrl+클릭 토글, 마퀴 드래그(카드 한정, 직계자식 교차). 핸들은 단일만.
- **3e-3 다중 이동**: R2 순서(캡처→promote→이동) + 집합 스냅 + compositeCmd.
- **3e-4 정렬·분배**: ALIGN/DISTRIBUTE 메시지 + 패널 6버튼/2버튼 + compositeCmd.
- **3e-5 수치 입력**: SET_RECT + rect emit + 패널 X/Y·W/H(로컬상태·blur커밋, 다중 X/Y=이동·W/H 읽기전용).
- **3e-6 undo 보편성**: textCmd(텍스트 커밋 포착) + detach 필터. 혼합 시나리오 역순 복원 검증.

## 검증 (무비용 런타임 관찰, `localhost:3000` Playwright)

1. Shift클릭 2개 → 집합 바운딩박스 표시, 8핸들 숨김. 다른 카드 클릭 → 그 카드로 리셋(D2).
2. 마퀴 드래그 → 교차 직계자식 일괄 선택. 카드 경계 넘는 요소 미선택.
3. 다중 드래그 → 전원 같은 delta 이동(R2로 상대위치 보존) + 스냅 가이드.
4. 정렬 좌/중/우·상/중/하 → 바운딩박스 기준 정렬. 분배(3개+) → 균등 간격.
5. 수치 X/Y 입력(Enter) → 반영. 다중 X/Y → 집합 이동. W/H 다중 → 읽기전용.
6. **undo 보편성**: (텍스트수정 → 다중이동 → 정렬) 3회 혼합 → Ctrl+Z 3번에 역순 완전 복원.
   버튼 ↶ 와 Ctrl+Z 동작 동일. 다중이동/정렬은 **undo 1회에 전원 복원**(compositeCmd).
7. 저장: `PATCH /deck/{id}` 200 → verify 갱신 + PNG `?v=` 증가. 직렬화에 `data-pi-*` 잔재 0,
   `data-screen-label` 7개 유지.

정적: 프론트 tsc + eslint(기존 `<img>` 경고 외 0). 백엔드 무변경(스모크 1회).

## 변경 파일 (핵심)

- `web/src/components/deck/editorAgent.ts` — 선택 모델·오버레이 풀·마퀴·다중이동·정렬/분배·SET_RECT·
  textCmd·serialize 공통마커. (주 변경, ES5·백틱금지 유지)
- `web/src/components/deck/DeckEditor.tsx` — `DeckEditorHandle`에 `align/distribute/setRect` 추가,
  `SelectedInfo`에 `count/rect/mixed/canDistribute` 추가, HISTORY/SELECTED 라우팅.
- `web/src/components/deck/DeckElementPanel.tsx` — 정렬 6버튼·분배 2버튼·수치 X/Y·W/H(로컬상태),
  다중선택 헤더(`선택: (다중 N)`), 단일전용 컨트롤 게이트.
- `web/src/app/deck/[jobId]/page.tsx` — 핸들 배선(align/distribute/setRect), 패널 props 전달. (경미)
- `scratchpad/seed_deck.py`, `scratchpad/drive_dm.py` — 재작성(하네스).
