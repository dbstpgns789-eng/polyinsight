# UI/UX Critique Report — 카드 에디터 (`/editor/[jobId]`)

> **대상**: `src/pages/editor/[jobId].astro`
> **날짜**: 2026-05-19
> **방법론**: LLM 디자인 리뷰 (독립) + 자동화 패턴 스캐너 (27개 패턴) 병렬 수행 후 종합
> **첫 실행** — 이전 트렌드 없음

---

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | 저장 4단계·위험도 카운터·내보내기 진행률 모두 구현됨 |
| 2 | Match System / Real World | 3 | "Image Slot"·"Template"·"Playwright" 등 영문/기술 용어 혼입 |
| 3 | User Control and Freedom | 3 | Esc·닫기 제공, 단 "확인 완료" 취소 불가·Ctrl+Z 미지원 |
| 4 | Consistency and Standards | 3 | 디자인 시스템 일관적, 단 정적 exportClose 리스너 사문화 버그 존재 |
| 5 | Error Prevention | 3 | CRITICAL 차단·자동저장 탄탄, 빈 필드 미검증 |
| 6 | Recognition Rather Than Recall | 3 | 위험도 이중 노출(필드+ActionBar) 우수, 썸네일 스크롤 어포던스 미제공 |
| 7 | Flexibility and Efficiency of Use | 2 | 탭 Arrow키 지원하나 Ctrl+S 미지원, 배치 작업 없음 |
| 8 | Aesthetic and Minimalist Design | 4 | 불필요 장식 없음, 계층 명확, 3패널 리듬 안정적 |
| 9 | Help Users Recover from Errors | 2 | 내보내기 재시도 구현, 저장 실패 원인·복구 방법 미제공 |
| 10 | Help and Documentation | 0 | 툴팁·도움말·온보딩 전무. CRITICAL/HIGH 의미 설명 없음 |
| **Total** | | **27/40** | **Acceptable — 출시 전 주요 개선 필요** |

---

## Anti-Patterns Verdict

### LLM Assessment

**AI 슬롭 판정: 해당 없음 (Negative).** 이 인터페이스는 AI 생성 UI의 전형적 징후를 회피하고 있다.

- **색상**: oklch 기반 포레스트 그린 팔레트 — AI 표준 blue/purple 계열이 아님. 브랜드 hue 152가 모든 토큰에 일관적으로 적용됨.
- **레이아웃**: 콘텐츠·미리보기·디자인 3패널 구조 — 카드 그리드 반복이 아닌 도메인-특화 에디터 레이아웃.
- **폰트**: Pretendard Variable — 국문 콘텐츠에 적합한 전문적 선택.
- **그라디언트 텍스트·글로우·글래스모피즘 없음.**
- **개성**: 위험도 색채 시스템(CRITICAL/HIGH/MEDIUM)과 미션-크리티컬한 확인 플로우가 도구에 명확한 목적감을 부여함.

전반적으로 "AI가 만들었을 것 같다"는 인상 없이 학술 논문 처리 도구로서의 정체성이 뚜렷하다.

### Deterministic Scan

자동화 스캐너(27개 패턴 감지)가 **1건** 플래그:

| # | 패턴 | 위치 | 스니펫 |
|---|------|------|--------|
| 1 | `layout-transition` (warning) | `[jobId].astro:842` | `.render-fill { transition: width 200ms linear; }` |

**분석**: `width` 속성 직접 애니메이션은 레이아웃 재계산(layout thrash)을 유발한다. LLM 리뷰와 자동 스캐너 결과가 일치하며, 이 1건은 false positive가 아닌 실제 성능 이슈다.

---

## Overall Impression

**잘 만든 도메인 도구가 도움말 없이 출시되려 한다.**

에디터의 뼈대 — 위험도 시스템, 저장 상태, 내보내기 플로우, 키보드 접근성 — 는 전문적으로 구현되어 있다. 그러나 학술 연구자가 처음 이 화면을 열었을 때 "CRITICAL 필드가 왜 내 내보내기를 막고 있는지", "confidence가 무엇인지", "Playwright가 뭔지"를 이해할 방법이 전혀 없다. 가장 큰 단일 기회는 **컨텍스트 도움말 레이어 추가**다.

---

## What's Working

**1. 위험도 이중 노출 시스템**

CRITICAL/HIGH 배지가 필드 인라인 배너와 ActionBar 카운터 양쪽에 동시 표시된다. 사용자는 현재 카드의 세부 위험과 전체 문서 위험을 시선 이동 없이 파악할 수 있다. 코드 에디터의 인라인 lint + 상태바 오류 카운트 패턴을 차용한 검증된 UX다.

**2. 내보내기 완료 애니메이션 (`done-pop`)**

380ms cubic-bezier pop 애니메이션으로 체크 아이콘이 등장하며 명확한 피크 순간을 제공한다. 피크-엔드 법칙에서 가장 중요한 "완료" 감정을 올바른 타이밍에 부여하고 있다.

**3. 저장 상태 4단계 + `aria-live`**

`저장 중 → 저장됨 → 미저장 → 저장 실패`의 4단계와 `aria-live="polite"` 구현은 스크린 리더 사용자를 포함해 항상 문서 상태를 인식할 수 있게 한다.

---

## Priority Issues

### [P0] 도움말 전무 — 위험도 시스템과 기술 용어 미설명

**What**: CRITICAL/HIGH/MEDIUM/confidence 등 핵심 개념에 대한 툴팁·인라인 도움말·온보딩이 전혀 없다. 내보내기 모달의 "Playwright로 카드를 생성하고 있습니다"도 학술 연구자에게 낯선 기술 용어다.

**Why it matters**: 신뢰가 핵심인 학술 논문 처리 도구에서 사용자가 "CRITICAL 필드"의 의미를 모르면 검증 없이 버튼을 누르게 되거나, 반대로 두려워서 이탈한다. Nielsen 10번 heuristic 0점.

**Fix**:
1. CRITICAL/HIGH/MEDIUM 배너에 `?` 아이콘 추가 → hover/click 시 툴팁: _"원문 수치와 AI 추출값이 불일치합니다. 원문을 확인 후 '확인 완료'를 눌러주세요."_
2. confidence 배지에 툴팁: _"AI가 이 값을 얼마나 확신하는지를 나타냅니다."_
3. 렌더링 sub-text에서 "Playwright" 제거 → _"고화질 PNG를 생성하고 있습니다."_

**Suggested command**: `/impeccable ux-writing`

---

### [P1] Ctrl+S (Cmd+S) 미지원

**What**: 에디터 환경에서 가장 기대되는 키보드 단축키가 없다.

**Why it matters**: 에디터에 익숙한 모든 사용자가 Ctrl+S를 누른다. 자동저장이 있어도 "지금 즉시 저장"에 대한 기대는 여전하다. 아무 반응이 없으면 저장 실패로 오해하거나 불안감을 느낀다.

**Fix**: `attachStaticListeners()`에 추가:
```js
document.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    clearTimeout(state.autoSaveTimer);
    doSave();
  }
});
```

**Suggested command**: `/impeccable harden`

---

### [P1] "확인 완료" 단방향 조작 — 취소 불가

**What**: CRITICAL 필드의 "확인 완료" 클릭 시 risk를 null로 설정하고 렌더링하지만, 이를 되돌리는 방법이 없다.

**Why it matters**: 원문 검증이 핵심 가치인 도구에서 검증 상태를 잘못 처리한 경우 복구 수단이 없다. 실수로 클릭하거나 재검토가 필요할 경우 신뢰가 무너진다.

**Fix**: "확인 완료" 클릭 후 risk를 null 대신 `'confirmed'`로 설정하여 필드에 "검토 완료" 뱃지를 유지하고 "다시 검토" 링크를 제공. 또는 5초 취소 가능한 토스트 제공.

**Suggested command**: `/impeccable harden`

---

### [P2] `width` 트랜지션 — 레이아웃 스래시 (자동 스캐너 확인)

**What**: `.render-fill { transition: width 200ms linear; }` — 진행률 바 width 직접 애니메이션. 자동화 스캐너 및 LLM 리뷰 양쪽에서 독립적으로 확인된 이슈.

**Why it matters**: `width` 변경은 매 프레임 레이아웃 재계산을 강제한다. 3초 렌더링 애니메이션 내내 layout thrash 발생. 저사양 기기에서 jank 유발 가능.

**Fix**:
```css
/* Before */
.render-fill { height: 100%; background: var(--accent); border-radius: 3px; width: 0%; transition: width 200ms linear; }

/* After */
.render-fill { height: 100%; background: var(--accent); border-radius: 3px; width: 100%; transform: scaleX(0); transform-origin: left; transition: transform 200ms linear; }
```
```js
/* startRendering() tick — Before */
fill.style.width = `${pct.toFixed(1)}%`;

/* After */
fill.style.transform = `scaleX(${(pct / 100).toFixed(3)})`;
```

**Suggested command**: `/impeccable animate`

---

### [P2] 영문 레이블 혼입 ("Image Slot", "Template")

**What**: 디자인 패널 섹션 레이블 "Image Slot"과 콘텐츠 패널 레이블 "Template"이 영문으로 표시된다. 나머지 인터페이스는 전부 한국어다.

**Why it matters**: 언어 전환은 인지 부하를 높이고, 번역이 누락된 것처럼 보여 완성도 인상을 낮춘다.

**Fix**: `"Image Slot"` → `"이미지 슬롯"`, `"Template"` → `"템플릿"`. HTML 2곳 수정.

**Suggested command**: `/impeccable ux-writing`

---

## Persona Red Flags

### 학술 연구자 "이수연" (프로젝트 특화 페르소나)

**프로필**: 논문은 자주 쓰지만 SaaS 툴은 익숙하지 않다. 데이터 정확성에 민감하고, 실수가 있으면 논문 신뢰성에 직결된다고 느낀다.

**Red flags**:
- `confidence: low` 배지가 왜 표시되는지 모른다 → 내용을 신뢰해야 할지 불안해한다.
- "CRITICAL 1건"이 내보내기를 막고 있는데 이유가 설명되지 않는다 → "왜 안 되지? 뭘 잘못 한 거지?" 패닉.
- "확인 완료"를 잘못 눌러 CRITICAL을 해제했는데 되돌릴 방법이 없다 → 원문 검증 목적이 무너진다.
- 렌더링 중 "Playwright" 언급 → "내 논문 데이터가 외부로 나가는 건 아닐까?" 불신.

### Alex (파워 유저)

**Red flags**:
- **Ctrl+S 없음** — 에디터 사용자에게 가장 치명적인 누락.
- 여러 카드의 CRITICAL 필드를 한 번에 확인(배치 처리)하는 방법이 없다. 카드 10장이면 탭을 하나씩 전환해야 한다.
- 내보내기 시작 키보드 단축키 없어 mouse-only 플로우 강제.

### Sam (접근성 의존 사용자)

**Red flags**:
- `.preflight-check` 아이콘이 시각적으로만 체크 여부를 전달한다. 스크린 리더용 텍스트 대안(`aria-label` 또는 숨겨진 텍스트) 없음.
- 위험도 배지 배경 대비율(`--risk-critical-subtle` 위 `--risk-critical` 텍스트) WCAG AA 4.5:1 미검증.
- 내보내기 DONE 상태의 개별 카드 다운로드 버튼("01", "02"...)에 기능이 연결되어 있지 않아 스크린 리더로는 실제 다운로드가 불가하다는 것을 알기 어렵다.

---

## Minor Observations

- **썸네일 스트립 스크롤 어포던스 없음**: `scrollbar-width: none`으로 스크롤바가 숨겨져 있어 카드 수가 많을 경우 더 있다는 사실을 알 수 없다. 양 끝 gradient fade mask 처리 권장.
- **`exportClose` 정적 리스너 사문화**: HTML의 `#export-close` 버튼은 첫 `renderExport()` 호출 시 `exportHeader.innerHTML` 교체로 DOM에서 분리된다. `attachStaticListeners()`에서 등록한 리스너가 실질적으로 동작하지 않는다. 각 phase의 동적 `#export-close-btn` 리스너가 실제 동작을 담당한다. 코드 혼선 정리 필요.
- **렌더링 진행률 바 가짜 3초**: 실제 서버 렌더링 시간과 무관한 고정 애니메이션이다. 실제 API 통합 시 서버-sent events 또는 폴링으로 진행률을 연동하지 않으면 100% 도달 후 실제 응답을 기다리는 어색한 UX가 발생한다.
- **미리보기 줌 컨트롤 없음**: 실제 내보내기 해상도는 1080×1080이지만 미리보기는 최대 400px이다. 텍스트 가독성을 실제 크기로 확인할 방법이 없다.
- **HIGH 필드의 "확인 완료" 버튼 정책 확인 필요**: 현재 구현에서 HIGH 필드도 "확인 완료" 버튼이 표시된다. 스펙 12번 문서에서 HIGH는 "주의 필요"이지 확인 완료 처리가 필요한지 명시되지 않았다.

---

## Questions to Consider

- **"CRITICAL 확인 완료를 되돌릴 수 있어야 하는가?"** — 원문 검증 도구의 핵심 신뢰 루프다. '5초 취소 토스트' vs '재-플래그 버튼' 중 무엇이 연구자 워크플로에 더 자연스러운가?
- **"Playwright라는 이름이 사용자에게 가치 있는 정보인가?"** — 렌더링 기술 스택 노출이 신뢰를 주는지, 아니면 불안을 주는지. 학술 연구자에게는 "고화질 렌더링 엔진"이 더 의미 있을 수 있다.
- **"카드가 20장이 넘어가면 어떤 UX가 필요한가?"** — 현재 탭 스트립은 20장 이상에서 스크롤이 길어진다. 카드 그룹핑, 점프 네비게이션이 필요한가?

---

## Trend

> **`src-pages-editor-jobid-astro` (첫 실행)**: 27/40
> Persisted → `.impeccable/critique/2026-05-19T01-34-22Z__src-pages-editor-jobid-astro.md`

---

## Recommended Action Plan

다음 이슈 카테고리가 발견됐다: **도움말 없음 (P0)**, **키보드 단축키·취소 불가 (P1×2)**, **애니메이션 성능·영문 레이블 (P2×2)**.

| 우선순위 | 커맨드 | 범위 |
|---------|--------|------|
| 1 | `/impeccable ux-writing` | CRITICAL/HIGH/confidence 툴팁 · "Playwright" 교체 · 영문 레이블 한국어화 |
| 2 | `/impeccable harden` | Ctrl+S 단축키 · "확인 완료" 취소 가능 처리 · exportClose 리스너 정리 |
| 3 | `/impeccable animate` | `.render-fill` → `transform: scaleX()` 교체 |
| 4 | `/impeccable polish` | 전체 마무리 패스 (위 수정 완료 후) |

> 한 번에 실행하거나 하나씩 진행하거나 원하는 순서로 요청해 주세요.
> 수정 완료 후 `/impeccable critique`를 재실행하면 점수 변화를 트래킹할 수 있습니다.
