# Phase 3 — 덱 편집기 (헌법 v3.0 WYSIWYG) 설계

> 2026-06-29 · 단일 저작 HTML 덱 위 편집. 레거시 필드 에디터(`/editor`)와 공존.

## Context

Phase 2에서 단일 저작 파이프라인이 발행급 standalone HTML 덱(`<!DOCTYPE html>` 한 덩어리,
카드별 `<div data-screen-label="NN" 1080×1350>`)을 만든다. 현재 `/deck/[jobId]`는 **view + export**만.
사용자는 이 덱을 고칠 수 없다 — 오타·문구·색 하나 바꾸려도 통째로 재생성해야 한다.

벤치마크에서 확정된 방향: **자유 HTML의 표현력은 지키되**(객체모델로 재감금 금지), 편집은
**A. 자연어(NL) 우선** + **C. 가벼운 직접조작**으로 한다. 자유 드래그/리사이즈는 객체모델을 요구해
v3.0 표현력을 재감금하므로 **보류**(추후 재논의).

## Goal

`/deck/[jobId]`에 "편집" 토글을 더해:
1. **직접조작(C)**: 카드 위 텍스트 클릭 → 인라인 수정 / 요소 선택 → 재스타일(폰트·색·크기·정렬)·삭제·순서변경.
2. **자연어(A)**: "표지 색을 더 차분하게", "3번 카드 제목 줄여" → AI가 현재 HTML을 패치.
3. 편집 후 **충실성 재검증(해자)** + **PNG 재렌더** → 뷰/검증 패널/export가 갱신된 결과 반영.

## Non-Goals (Phase 3 아님)

- 자유 드래그·자유 리사이즈·자유 레이아웃 재배치 (객체모델 = v3.0 재감금 → **보류**).
- 레거시 필드 에디터(`/editor`, CardEditorData, 30 React 레이아웃) 수정 — **무손상 공존**.
- 협업/버전히스토리/undo 스택 (Phase 4+ 후보). Phase 3은 **단일 최신본 덮어쓰기** + 재생성 안전망.

## 아키텍처 — iframe + postMessage

저작 결과가 **완전한 HTML 문서**(자체 `<head><style>`, CDN 폰트)이므로 `dangerouslySetInnerHTML`로
div에 박으면 (a)문서 레벨 HTML이 깨지고 (b)카드 CSS가 부모 앱으로 누수되고 (c)편집 중 화면과
export PNG가 어긋난다. → **iframe에 통째로 마운트**한다.

```
부모(React, /deck/[jobId])
  <iframe srcDoc={html} sandbox="allow-scripts allow-same-origin">
      └─ 주입된 editorAgent.ts (편집 모드일 때만 활성)
         · 클릭 → 가장 가까운 편집가능 요소 선택, 하이라이트 오버레이
         · 텍스트 요소 → contentEditable, blur 시 dirty 표시
         · 직렬화는 iframe **내부 스크립트가** 수행(부모가 contentDocument를 읽지 않음)
  ↕ postMessage 프로토콜
  부모 패널: DeckElementPanel(재스타일/삭제/순서) + DeckNLBar(자연어)
```

**왜 주입 스크립트가 직렬화하나**: 부모가 `iframe.contentDocument.documentElement.outerHTML`을 직접
읽으면 편집 아티팩트(하이라이트 오버레이·contentEditable 속성·data-edit-id)가 섞인다. 주입
스크립트가 **클린 복제본**에서 아티팩트를 제거하고 직렬화한 HTML만 부모로 보낸다.

### postMessage 프로토콜

부모 → iframe:
| type | payload | 동작 |
|---|---|---|
| `SET_MODE` | `{mode:'view'｜'edit'}` | 편집 핸들러·하이라이트 on/off |
| `GET_HTML` | — | 클린 직렬화 HTML을 `HTML`로 회신 |
| `APPLY_STYLE` | `{prop, value}` | 선택 요소에 인라인 스타일 적용 |
| `DELETE_ELEMENT` | — | 선택 요소 제거 |
| `MOVE_ELEMENT` | `{dir:'up'｜'down'}` | 형제 순서 교환 |
| `CLEAR_SELECTION` | — | 선택 해제 |
| `SET_HTML` | `{html}` | (NL 패치 결과) 문서 전체 교체 |

iframe → 부모:
| type | payload | 의미 |
|---|---|---|
| `EDITOR_READY` | — | 주입 스크립트 init 완료 |
| `SELECTED` | `{tag, styles, text}` | 요소 선택됨(패널 동기화) |
| `DESELECTED` | — | 선택 해제됨 |
| `DIRTY` | — | 사용자가 내용 변경(저장 버튼 활성) |
| `HTML` | `{html}` | GET_HTML 응답(클린) |

**선택 단위**: 클릭한 노드에서 시작해 "의미 단위"(텍스트 블록·박스·이미지·SVG 그룹)까지 등반.
각 편집가능 요소에 주입 스크립트가 `data-edit-id`를 부여(직렬화 시 제거). 텍스트는 그 자리에서
contentEditable; 박스/이미지/SVG는 패널 재스타일·삭제·이동 대상.

## 백엔드 변경

### 1. `paper_text` 영속화 (재검증 전제 — 필수 선행)

`verify_deck(html, paper_text)`는 원문이 있어야 재검증한다. 현재 파이프라인은 `s1_out.raw_text`를
저장하지 않는다 → 편집본 재검증 불가.

- `db.py`: `authored_deck`에 `paper_text TEXT` 컬럼 추가 + **idempotent 마이그레이션**
  (`PRAGMA table_info`로 존재 확인 후 없으면 `ALTER TABLE ... ADD COLUMN`). 기존 행은 NULL.
- `save_authored_deck(...)`에 `paper_text` 인자 추가, `get_authored_deck`이 반환에 포함.
- `pipeline.py`: 저작 후 `save_authored_deck(..., paper_text=s1_out.raw_text)`.
- **기존(NULL) 덱 폴백**: 편집 저장 시 `paper_text`가 NULL이면 재검증을 건너뛰고 기존 verify_json을
  유지하되 경고 1건(`"이 덱은 재검증 불가 — 재생성 시 검증 복원"`)을 표면화. **막지 않음**(헌법 3조).

### 2. `PATCH /api/deck/{job_id}` — 직접조작 저장

```
입력: {html}  (iframe이 직렬화한 클린 HTML)
처리: data-screen-label 존재 가드 → verify_deck(html, paper_text) 재실행(원문 있을 때)
      → save_authored_deck(갱신) → render_deck(html)로 PNG 재생성 → card_images 갱신
출력: {verify, cardCount, warnings}
```
재렌더는 동기(Playwright 수 초). 응답에 새 verify 동봉 → 패널 즉시 갱신. PNG는 캐시 무력화를 위해
프론트가 `?v=updatedAt` 쿼리로 재요청.

### 3. `POST /api/deck/{job_id}/nlpatch` — 자연어 편집

```
입력: {instruction}
처리: nl_patch.apply(html, instruction, paper_text) →
      llm_client.call(model=LLM_MODEL_AUTHOR, system=수정 전용 프롬프트, ...)
      프롬프트 계약: "주어진 HTML을 최소 변경으로 수정. 출력 계약(data-screen-label·1080×1350·
      인라인 스타일·코드펜스 금지) 유지. 지시 밖 요소 보존. 충실성 규칙 유지."
      → verify_deck 재실행 → save → render
출력: {html, verify, cardCount, warnings}
```
**비용 작업** → 실행 전 사용자 허락(메모리 규칙). UI는 NL 전송을 명시적 버튼으로(자동 호출 금지).
신규 파일 `backend/agents/deck/nl_patch.py` + `backend/agents/deck/edit_prompts.py`(수정 전용 시스템 프롬프트).

## 프론트엔드 변경

- **신규** `web/src/components/deck/DeckEditor.tsx` — iframe 마운트 + postMessage 브리지(ref·메시지 라우팅).
- **신규** `web/src/components/deck/editorAgent.ts` — iframe에 주입되는 순수 JS 문자열(클릭 선택·
  하이라이트·contentEditable·클린 직렬화). 빌드 시 문자열로 임베드(번들 분리).
- **신규** `web/src/components/deck/DeckElementPanel.tsx` — 선택 요소 재스타일(색·폰트크기·정렬)·삭제·순서.
- **신규** `web/src/components/deck/DeckNLBar.tsx` — 자연어 입력 + 전송(명시적).
- **수정** `web/src/app/deck/[jobId]/page.tsx` — "보기/편집" 토글. 편집 모드면 PNG 피드 대신 DeckEditor +
  패널. "저장" → patchDeck. 저장 후 verify 패널·export는 갱신본 사용.
- **수정** `web/src/lib/api.ts` — `patchDeck(jobId, html)`, `nlPatchDeck(jobId, instruction)`.

## 구현 슬라이스

- **3a (텍스트 편집 + 저장 배관)**: iframe 마운트 → contentEditable 텍스트 → GET_HTML → `paper_text`
  영속화 + PATCH 엔드포인트 + 재검증/재렌더 → 저장 후 갱신 확인. **여기까지가 핵심 골격.**
- **3b (선택 + 재스타일)**: 요소 선택·하이라이트·DeckElementPanel(색/폰트/정렬/삭제/순서) → APPLY_STYLE 등.
- **3c (자연어 본체)**: DeckNLBar + nlpatch 엔드포인트 + 수정 프롬프트. 실 LLM(유료) → 허락 후.

## 검증 (verify 스킬 — 런타임 관찰)

- **무비용**: `DEV_MOCK_LLM=True` + 실 PDF 업로드 → `/deck/[jobId]` 편집 토글 → 텍스트 수정 → 저장 →
  PNG·검증 패널 갱신 육안 확인(브라우저). pytest `backend/tests/`: paper_text 라운드트립, PATCH
  재검증·재렌더(7장), 마이그레이션 idempotency, NULL 폴백 경고.
- **유료(허락 후)**: 3c nlpatch 1회 — 실 지시로 최소 변경·계약 유지·충실성 보존 확인.
- 코드 변경 후 uvicorn 수동 재시작(메모리 규칙).

## 리스크 / 결정

- **iframe sandbox**: `allow-scripts allow-same-origin` 필요(주입 스크립트·폰트). srcDoc은 동일 출처.
- **직렬화 신뢰경계**: 부모는 iframe이 보낸 HTML 문자열만 신뢰(클린 직렬화 책임은 주입 스크립트).
  서버는 PATCH 입력에 `data-screen-label` 가드 + 길이 상한.
- **재렌더 비용**: 매 저장마다 Playwright 7장 — 동기 수 초. 과하면 후속 디바운스/큐잉.
- **undo 없음**: Phase 3은 단일 덮어쓰기. 안전망 = 언제든 재생성(원본 파이프라인). 명시적 경고.
