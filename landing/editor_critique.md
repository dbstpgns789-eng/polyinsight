# 카드 에디터 UI/UX Critique Report

> 대상: `src/pages/editor/[jobId].astro`  
> 기준: Nielsen 10 Heuristics + 실제 코드 정합성 + 제품 플로우 일관성  
> 작성일: 2026-05-18

---

## 요약 점수

| 영역 | 점수 | 비고 |
|------|------|------|
| 정보 구조 (IA) | 7/10 | 3패널 구조 명확, 탭 ARIA 미완성 |
| 시각 디자인 | 8/10 | 디자인 토큰 일관성 우수, 소수 이슈 |
| 인터랙션 | 5/10 | 카드 전환 시 상태 버그 다수 |
| 접근성 | 5/10 | ARIA 패턴 오류, 포커스 트랩 미구현 |
| 피드백/안내 | 6/10 | 위험도 배너 OK, 빠진 피드백 존재 |
| 전체 | **6.2/10** | |

---

## P1 — 버그 (기능 오작동)

### P1-1. 카드 전환 시 이미지 슬롯 상태 미동기화

**현상**: 카드 A에 이미지를 업로드한 후 카드 B로 전환해도 이미지 슬롯 UI가 리셋되지 않음. `selectCard()`가 `img-empty` / `img-filled` / `img-preview.src`를 갱신하지 않음.

**코드 위치**: `selectCard()` 함수 — `renderContentPanel()` 호출 후 이미지 슬롯 상태 없음.

```js
// 현재: 이미지 슬롯 갱신 없음
function selectCard(idx) {
  state.cardIdx = idx;
  renderCardTabs();
  renderThumbnails();
  renderContentPanel();
  renderPreviewCard();
}

// 필요: 이미지 슬롯 동기화 추가
function syncImageSlot() {
  const hasImg = state.cards[state.cardIdx].hasImage;
  document.getElementById('img-empty').hidden  = hasImg;
  document.getElementById('img-filled').hidden = !hasImg;
  // src는 카드별로 저장한 objectURL로 복원
}
```

---

### P1-2. Export 모달 정적 닫기 버튼 미연결

**현상**: HTML에 `id="export-close"` 버튼이 있으나 `attachStaticListeners()`에서 이 버튼을 연결하지 않음. `renderExport()` 내부에서 새 버튼을 주입하는 방식이라 정적 버튼은 동작 안 함.

**코드 위치**: `[jobId].astro` L122–128 (HTML), `attachStaticListeners()` — `exportClose` 변수 선언만 있고 이벤트 없음.

**수정**: `attachStaticListeners()` 내부에 `exportClose?.addEventListener('click', closeExport)` 추가 또는 정적 버튼 제거.

---

### P1-3. MEDIUM / HIGH 위험 필드 명시적 해소 불가

**현상**: CRITICAL 필드만 "확인 완료" 버튼이 있음. HIGH 필드는 배너만 표시되고 사용자가 명시적으로 해소할 수 없음. 그러나 ActionBar의 내보내기 버튼은 HIGH까지 막음 — 사용자가 어떻게 HIGH를 해소해야 하는지 알 수 없음.

**결과**: 내보내기 영구 차단 상태가 될 수 있음.

**수정**: HIGH 필드에도 "확인 완료" 버튼 추가. 또는 HIGH는 경고만이고 내보내기를 막지 않는 방향 중 선택.

---

### P1-4. Preflight 체크리스트 항상 "완료" 표시

**현상**: 내보내기 버튼이 CRITICAL/HIGH 존재 시 비활성화되어 있어 preflight 진입 자체가 차단되는 것이 맞음. 그런데 preflight 화면의 세 번째 항목 "CRITICAL/HIGH 필드 검토 완료"에 항상 녹색 체크가 표시됨 — 실제로는 미해소 건이 있을 수 있는 상태에서 진입 가능한 경우를 고려하면 신뢰 저하.

---

## P2 — UX 결함 (흐름/피드백 이슈)

### P2-1. 카드 미리보기 수직 정렬

**현상**: `.preview-stage { align-items: flex-start }` — 카드가 패널 상단에 붙어서 표시됨. 패널이 카드보다 높을 때 시각적 무게중심이 어색함.

**수정**: `align-items: center`로 변경.

---

### P2-2. 썸네일이 실제 카드 내용을 반영하지 않음

**현상**: 썸네일 56×56px에 초록 헤더 바 + 숫자만 표시. 카드 타입/위험도/이미지 여부 등 어떤 정보도 없음. 카드가 많아지면 탐색 불가.

**개선안**: 최소한 위험도 도트(CRITICAL=빨강, HIGH=주황) 또는 템플릿 아이콘을 썸네일에 추가.

---

### P2-3. 뒤로가기 버튼 목적지 불일치

**현상**: 버튼 텍스트 "대시보드", `href="/"` — 대시보드가 아닌 홈(랜딩페이지)으로 이동.

**수정**: 스펙(`12_card_editor_content.md`)은 `/dashboard`이나 현재 대시보드 페이지가 없으므로 텍스트를 "홈으로" 또는 href를 추후 `/dashboard`로 변경 예정임을 주석으로 명시.

---

### P2-4. 원본값 복원 수단 없음

**현상**: textarea를 수정하면 AI가 생성한 원본값으로 돌아갈 방법이 없음. 자동저장까지 되면 영구 손실.

**개선안**: 필드 헤더에 "원본으로 되돌리기" 아이콘 버튼 추가 (원본값을 `INITIAL.cards`에서 참조).

---

### P2-5. 파일명 전체 확인 불가

**현상**: `.topbar__filename { max-width: 260px; text-overflow: ellipsis }` — 긴 파일명이 잘리나 hover tooltip이 없음.

**수정**: `title` 속성 추가로 네이티브 툴팁 제공.

---

### P2-6. textarea 고정 rows="3"

**현상**: 모든 필드가 동일하게 3행. 짧은 title은 공간 낭비, 긴 body 필드는 스크롤 발생.

**개선안**: `rows` 값을 필드 타입별로 분기 (title: 2, body/description: 4).

---

### P2-7. 카드 전환 시 스크롤 위치 유지

**현상**: 카드를 전환하면 콘텐츠 패널의 스크롤 위치가 유지됨. 이전 카드를 아래까지 스크롤하고 다음 카드로 전환하면 스크롤이 중간에 남아있음.

**수정**: `selectCard()` 내에서 `.panel-scroll` 스크롤을 0으로 초기화.

---

## P3 — 접근성

### P3-1. ARIA Tab 패턴 미완성

**현상**: `role="tablist"` + `role="tab"` 사용했으나 대응하는 `role="tabpanel"` 없음. 또한 탭 간 키보드 화살표 이동(Left/Right) 미구현. ARIA Authoring Practices 위반.

**수정**: 
- 패널에 `role="tabpanel"` + `aria-labelledby` 추가
- 탭에 keydown 이벤트로 `ArrowLeft`/`ArrowRight` 탐색 구현

---

### P3-2. 모바일 차단 화면 aria-hidden

**현상**: `<div class="mobile-blocker" aria-hidden="true">` — 모바일에서 유일한 콘텐츠가 스크린리더에 무시됨.

**수정**: `aria-hidden="true"` 제거. 모바일 사용자에게도 텍스트가 읽혀야 함.

---

### P3-3. Export 모달 포커스 트랩 미구현

**현상**: 내보내기 모달이 열려 있을 때 Tab 키로 배경 에디터 요소까지 접근 가능.

**수정**: 업로드 모달(`UploadModal.astro`)에 구현된 포커스 트랩 패턴 동일하게 적용.

---

### P3-4. 위험 배너 role="alert" 중복 발화 가능성

**현상**: 카드를 전환할 때마다 `role="alert"`가 포함된 CRITICAL 배너가 DOM에 재삽입됨. 일부 스크린리더는 이를 반복 발화함.

**수정**: `renderContentPanel()` 시 기존 DOM을 교체하는 대신 내용만 갱신하거나, `aria-live="polite"` 컨테이너를 별도로 두고 알림을 한 번만 발화.

---

## P4 — 코드 품질 / 기술적 이슈

### P4-1. 죽은 CSS 코드

`fs-state`, `loader`, `loader-ring`, `@keyframes spin` 규칙이 남아있으나 로딩/에러 상태 HTML을 제거했으므로 미사용.

**수정**: 해당 CSS 블록 제거.

---

### P4-2. `btn-sm` 전역 클래스 충돌 위험

`.btn-sm`이 scoped style에 선언됨. 동일한 클래스가 다른 페이지에도 사용될 경우 Layout.astro의 글로벌 `.btn`과 충돌 가능.

---

### P4-3. innerHTML XSS 노출면

`buildCardHTML()` 내에서 `f.title`, `f.body` 등 사용자가 수정한 텍스트를 `innerHTML`로 직접 주입. 현재 mock 환경에서는 문제없으나, 백엔드 연동 후 서버 응답값이 그대로 들어오면 XSS 가능성 있음.

**수정 방향**: `textContent` 기반 DOM 조작 또는 `DOMPurify` 적용.

---

## 잘 된 점

| 항목 | 평가 |
|------|------|
| 디자인 토큰 일관성 | `oklch` 색상 체계가 랜딩페이지와 완전 일치 |
| CRITICAL 배너 | 출처(섹션, 페이지) 표시 + 확인 완료 버튼 — 스펙 완전 구현 |
| 자동저장 피드백 | 4가지 상태 뱃지가 명확하고 색상 구분 직관적 |
| Container Query 미리보기 | `cqw` 단위 스케일링 — 크기에 상관없이 카드 비율 유지 |
| ActionBar 조건부 잠금 | CRITICAL/HIGH 존재 시 내보내기 버튼 비활성 + 툴팁 — 오용 방지 |
| Export Modal 4단계 | PREFLIGHT → RENDERING → DONE → ERROR 상태머신 완전 구현 |
| 이미지 삭제 hover 노출 | UX 패턴 적절, 실수 삭제 방지 |

---

## 수정 우선순위 요약

| 순위 | 항목 | 난이도 |
|------|------|--------|
| 🔴 P1 | 이미지 슬롯 카드 전환 버그 (P1-1) | 낮음 |
| 🔴 P1 | HIGH 필드 확인 완료 버튼 없음 (P1-3) | 낮음 |
| 🔴 P1 | Export 정적 닫기 버튼 미연결 (P1-2) | 낮음 |
| 🟠 P2 | 미리보기 수직 정렬 (P2-1) | 낮음 |
| 🟠 P2 | 카드 전환 스크롤 초기화 (P2-7) | 낮음 |
| 🟠 P2 | 뒤로가기 목적지 (P2-3) | 낮음 |
| 🟠 P2 | 파일명 tooltip (P2-5) | 낮음 |
| 🟡 P3 | 모바일 차단 aria-hidden 제거 (P3-2) | 낮음 |
| 🟡 P3 | Export 모달 포커스 트랩 (P3-3) | 중간 |
| 🟡 P3 | Tab ARIA 패턴 완성 (P3-1) | 중간 |
| ⚪ P4 | 죽은 CSS 정리 (P4-1) | 낮음 |
| ⚪ P4 | innerHTML XSS 대비 (P4-3) | 백엔드 연동 시 |

---

*이 리포트는 코드 정적 분석 기반. 실제 브라우저 렌더링 후 시각적 이슈가 추가 발견될 수 있음.*
