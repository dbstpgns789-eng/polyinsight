# 덱 비주얼 직접조작 MVP (Phase 3d) 설계

> 2026-06-30 · 단일 저작 HTML 덱 위 마우스 직접조작. iframe WYSIWYG(Phase 3a~3c)의 연장.

## Context

헌법 v3.0에서 덱은 **AI가 저작한 자유 HTML 한 덩어리**다. Phase 3에서 텍스트 직접수정(3a)·요소
국소 재스타일(3b)·자연어 패치(3c)를 붙였지만 **마우스로 요소를 옮기고 크기를 바꾸는 직접조작이
없다.** 디자이너·파워유저가 "AI 딸깍밖에 안 되네"라며 산출물을 다운받아 Figma·그림판으로
가져가 편집을 이어가면 그건 제품 실패다 — 편집은 우리 안에서 완결돼야 한다.

이 작업은 그 완결성의 본체: **하이브리드 드래그 이동 + 8방향 리사이즈 + 풀 스냅/정렬 가이드 +
undo/redo + 경계 가드**를, 객체모델로 자유 HTML을 재감금하지 않고(헌법 §1) iframe 내부에서
DOM을 직접 조작하는 방식으로 구현한다.

**설계 원칙**: HTML(DOM)은 항상 유일한 사실 소스. 편집 모델은 그 위의 레이어지 대체물이 아니다.
→ v3.0 정합 + 미래의 풀 Figma 확장을 재작성 없이 흡수.

## 아키텍처 (A · iframe 내부 `editorAgent` 확장)

드래그/리사이즈/스냅/직렬화 모두 주입 스크립트가 iframe **내부 좌표**(자연 1080px 공간)에서
처리한다 → 부모의 `transform:scale` 축소와 무관하게 정확, sandbox 신뢰경계 유지. 부모 React는
명령(undo/redo·흐름복귀)만 보내고 상태(SELECTED/DIRTY/HISTORY_STATE)를 받는다. 실제 마우스
드래그는 iframe이 자율 처리.

> B(부모 React 오버레이)는 scale 좌표 매핑·sandbox 제약으로, C(닫힌 객체모델 추출)는 v3.0
> 재감금·복잡도로 탈락. **단 C-좋음(DOM을 사실 소스로 둔 편집 레이어)은 다음 단계의 열린 토론
> 지점으로 둔다 — 영구 배제는 'C-나쁨'(닫힌 스키마로 HTML 대체) 뿐.**

## 모듈 (`editorAgent`를 `__pi` 네임스페이스로 구조화)

주입 스크립트는 단일 IIFE이되 책임을 `window.__pi` 네임스페이스 객체로 분리한다. 1차는 한 파일
(`editorAgent.ts`) 안에 모듈 객체로, 후속에 파일 분할 가능(표면 계약 동일).

| 모듈 | 책임 | 상태 |
|---|---|---|
| `selection` | 클릭→의미요소 선택, 하이라이트 오버레이 | 기존 |
| `transform` | 하이브리드 드래그 이동 + 8방향 리사이즈 → 인라인 스타일 | 신규 |
| `snap` | 형제·카드 가장자리/중심 정렬 + 등간격 + 안전영역 스냅·가이드 | 신규 |
| `history` | undo/redo **커맨드 스택**(do/undo 역연산) — C-좋음 씨앗 | 신규 |
| `serialize` | 편집 아티팩트 제거 + 클린 HTML 직렬화 | 기존·확장 |
| `bridge` | postMessage 라우팅, EDITOR_READY/HEIGHT | 기존 |

## 동작 사양

**선택** (기존 `pick`/`isTextLeaf` 재사용)
텍스트 리프는 `contentEditable`. 그 외(박스·이미지·SVG 그룹)는 드래그/리사이즈 대상. 카드
프레임(`data-screen-label`)은 선택/이동 제외.

**이동 (하이브리드)**
- 드래그 시작 → 흐름 요소면 **그 요소만** `position:absolute` 승격. 부모 카드에 `position:relative`
  없으면 인라인 보장(레퍼런스 덱은 이미 relative).
- 드래그 중 `transform:translate(dx,dy)`(리플로우 없음), drop 시 `transform` 제거하고 카드 기준
  `left/top`(= childRect − cardRect)로 확정.
- 경계 가드: `left/top`을 [0, 1080−w]×[0, 1350−h]로 클램프(카드 `overflow:hidden`).

**리사이즈 (8방향 핸들)**
선택 오버레이에 8핸들(`data-pi-handle`). 드래그→`width/height`(+ 방향별 `left/top`). 텍스트는
width 재흐름(글자 크기는 `DeckElementPanel`의 +/− 담당, 분리 유지).

**스냅 (풀)**
이동/리사이즈 중 형제·카드 가장자리(좌/우/상/하)·중심(가로/세로)·안전영역(카드 padding) 근접 시
스냅 + 분홍 가이드선(`data-pi-guide`). 형제 간격이 같아지면 등간격(`=`) 배지. 임계 ~6px(자연 좌표).

**undo/redo (`history`) — 커맨드 패턴 (C-좋음 씨앗)**
각 편집을 **Command 객체** `{do, undo}`로 표현(스냅샷 아님): `Move{el, from→toStyle}`,
`Resize{el, from→toRect}`, `Style{el, prop, from→to}`, `Delete{el, parent, nextSibling}`,
`MoveOrder`, `RevertFlow`. 커밋=`do()`+push, undo=`undo()` 역연산, redo=`do()`. 선택 상태 보존,
스냅샷보다 정밀·경량. **다중선택(다음 단계)은 `CompositeCommand`로 확장만** → 리팩터 불필요.
`Ctrl+Z`/`Ctrl+Shift+Z`(또는 `Ctrl+Y`) + 부모 버튼. 각 조작 후 `HISTORY_STATE{canUndo,canRedo}` 통보.

**흐름 복귀**
패널 버튼 → 선택 요소의 인라인 `position/left/top/transform` 제거 → 원래 흐름으로(자유배치
실수 안전망). `RevertFlow` 커맨드로 undo 가능.

**직렬화 (`serialize` 확장)**
클린 복제본에서 제거: `[data-pi-overlay]`, `[data-pi-agent]`, `[data-pi-handle]`,
`[data-pi-guide]`, `contenteditable`. 확정 `position/left/top/width/height` 인라인 스타일은 보존
(편집 결과). `transform`은 drop 시 이미 제거됨.

## postMessage 프로토콜 확장

기존: 부모→ `SET_MODE/GET_HTML/APPLY_STYLE/DELETE_ELEMENT/MOVE_ELEMENT/CLEAR_SELECTION`;
에이전트→ `EDITOR_READY/HEIGHT/SELECTED/DESELECTED/DIRTY/HTML`.

추가:
- 부모→에이전트: `UNDO`, `REDO`, `REVERT_FLOW`
- 에이전트→부모: `HISTORY_STATE {canUndo, canRedo}` (DIRTY는 드래그/리사이즈 커밋 시에도 발화)

드래그/리사이즈 자체는 에이전트 내부 마우스 이벤트로 자율 처리.

## 부모 React 변경

- `DeckEditor.tsx` — `DeckEditorHandle`에 `undo()/redo()/revertFlow()`, `HISTORY_STATE` 수신→콜백,
  핸들 메시지 라우팅. (srcDoc·scale·HEIGHT 로직 그대로)
- `DeckElementPanel.tsx` — 선택 요소에 "흐름으로 복귀" 버튼(absolute일 때만).
- `app/deck/[jobId]/page.tsx` — 편집 헤더에 undo/redo 버튼(+`HISTORY_STATE` 활성/비활성), 키보드
  단축키 위임. **저장은 기존 `handleSave`(getHtml→`patchDeck`→재검증·재렌더·PNG `?v=`) 그대로.**

## 백엔드 변경: 없음

직렬화 HTML은 인라인 스타일만 늘 뿐 계약(`data-screen-label`·1080×1350) 유지 → 기존
`PATCH /api/deck/{job_id}` + `persist_edited_deck`(재검증+`render_deck`+`delete_card_images_above`)가
그대로 처리. 신규 엔드포인트/DB 변경 불필요.

## 구현 슬라이스

- **3d-1 (이동)**: `__pi` 구조화 + `transform`(하이브리드 드래그+경계) + `serialize` 확장 +
  `history`(커맨드) + 부모 undo 버튼/단축키. drag→absolute 확정→저장→재렌더 골격.
- **3d-2 (리사이즈)**: 8핸들 + width/height + 흐름복귀 버튼.
- **3d-3 (스냅)**: 정렬선/등간격/안전영역 가이드.

각 슬라이스 후 `tsc`/eslint + Playwright 런타임 드라이브.

## 검증 (런타임 관찰 — 무비용)

계정+덱 시드 → uvicorn + `next dev` → **`localhost:3000`** Playwright 쿠키 주입:
1. 드래그: `position:absolute` 승격 + `left/top` 변경 + 분홍 가이드 + 좌표가 scale과 무관(자연 좌표).
2. 리사이즈 핸들: `width/height` 변경.
3. 경계 밖 드래그: `left/top` 클램프.
4. undo(커맨드 역연산) 복원 / 흐름 복귀: 인라인 position 제거·흐름 재배치.
5. 저장: `PATCH /deck/{id}` 200 → verify 갱신 + PNG `?v=` 증가. 보기 모드 새 위치 육안 확인.
6. 직렬화 청결성: 저장 HTML에 `data-pi-*`·`contenteditable` 잔재 0, `data-screen-label` 7개 유지.

정적: 프론트 `tsc` + eslint(기존 `<img>` 경고 외 0). 백엔드 무변경(스모크 1회).

## 다음 단계 로드맵 (풀 Figma / C 레이어 진화)

여러 에픽으로 분해. 각 단계는 기존 모듈 확장으로 흡수(재작성 없음):

| # | 기능 | 확장 모듈 | 의존 | 메모 |
|---|---|---|---|---|
| 0 | 코드(HTML/CSS) 직접편집 탈출구 | 부모 패널 + 기존 PATCH | — | 표현 100% 자유. 디자이너 이탈 즉시 방지. 최저비용. |
| 1 | 다중선택 | `selection`(→`Set`) | — | 2·4의 전제. |
| 2 | 정렬·분배 | `transform`+`align` | 1 | 다중선택 위에 싸게. |
| 3 | 레이어 패널 | 부모 패널+`bridge` | — | DOM 트리 그대로 노출. |
| 4 | 그룹화 | DOM wrapper+`transform` | 1 | 진짜 그룹=wrapper(손실 0). |
| 5 | 회전 | `transform`+`snap` | (1) | 비축 바운딩 = 풀 Figma 진짜 난관. |
| 6 | 펜툴/도형 | `draw`(신규) | — | "저작" 경계, 3c와 중복 가능 → ROI 재평가. |

**C 레이어**: 다중선택·그룹·회전이 쌓이면 "선택 집합 + 변환 + 커맨드 스택"이 인메모리 편집
모델로 응집(= C-좋음). MVP `history`가 **이미 커맨드 패턴**이라 교체 불필요 — `CompositeCommand`로
확장만. C 도입 여부는 **열린 토론 지점**.

**YAGNI**: 0+1+2+3 + 자연어/코드 탈출구가 이탈방지 충분선일 공산. 4·5·6은 실유저 신호 게이트.
회전은 최후·신중(삼각함수), 펜툴은 ROI 재평가.

## 비목표

협업/실시간 커서, 버전 히스토리 영속화(현재 세션 undo만), 반응형 멀티 사이즈 자동 리플로우.
