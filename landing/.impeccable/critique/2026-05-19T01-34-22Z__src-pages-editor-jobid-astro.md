---
timestamp: 2026-05-19T01-34-22Z
slug: src-pages-editor-jobid-astro
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | 저장 4단계, 위험도 카운터, 내보내기 진행률 모두 구현됨 |
| 2 | Match System / Real World | 3 | "Image Slot" · "Template" · "Playwright" 등 영문/기술 용어 혼입 |
| 3 | User Control and Freedom | 3 | Esc·닫기 제공, 단 "확인 완료" 취소 불가 · Ctrl+Z 미지원 |
| 4 | Consistency and Standards | 3 | 디자인 시스템 일관적, 단 정적 exportClose 리스너 사문화 버그 존재 |
| 5 | Error Prevention | 3 | CRITICAL 차단·자동저장 탄탄, 빈 필드 미검증 |
| 6 | Recognition Rather Than Recall | 3 | 위험도 이중 노출(필드+ActionBar) 우수, 스크롤 어포던스 미제공 |
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
- **그라디언트 텍스트·글로우·글래스모피즘 없음**.
- **개성**: 위험도 색채 시스템(CRITICAL/HIGH/MEDIUM)과 미션-크리티컬한 확인 플로우가 도구에 명확한 목적감을 부여함.

전반적으로 "AI가 만들었을 것 같다"는 인상 없이 학술 논문 처리 도구로서의 정체성이 뚜렷하다.

### Deterministic Scan

자동화 스캐너(27개 패턴 감지)가 **1건** 플래그:

| # | 패턴 | 위치 | 스니펫 |
|---|------|------|--------|
| 1 | `layout-transition` (warning) | `[jobId].astro:842` | `.render-fill { transition: width 200ms linear; }` |

**분석**: `width` 속성 직접 애니메이션은 레이아웃 재계산(layout thrash)을 유발한다. `.render-fill`의 진행률 바는 `transform: scaleX()` + `transform-origin: left`로 교체하면 GPU 합성 레이어에서 처리되어 성능이 개선된다.

LLM 검토가 추가 발견한 내용: `exportClose` 정적 리스너 사문화, Ctrl+S 미지원, 도움말 전무, "확인 완료" 취소 불가. 스캐너가 놓친 UX 품질 이슈 5건.

---

## Overall Impression

**잘 만든 도메인 도구가 도움말 없이 출시되려 한다.**

에디터의 뼈대 — 위험도 시스템, 저장 상태, 내보내기 플로우, 키보드 접근성 — 는 전문적으로 구현되어 있다. 학술 연구자가 처음 이 화면을 열었을 때 "CRITICAL 필드가 왜 내 내보내기를 막고 있는지", "confidence가 무엇인지", "Playwright가 뭔지"를 이해할 방법이 전혀 없다. 가장 큰 단일 기회는 **컨텍스트 도움말 레이어 추가**다.

---

## What's Working

**1. 위험도 이중 노출 시스템**
CRITICAL/HIGH 배지가 필드 인라인 배너와 ActionBar 카운터 양쪽에 동시 표시된다. 사용자는 현재 카드의 세부 위험과 전체 문서 위험을 시선 이동 없이 파악할 수 있다. 이 패턴은 코드 에디터의 인라인 lint + 상태바 오류 카운트에서 차용한 검증된 패턴이다.

**2. 내보내기 완료 애니메이션 (`done-pop`)**
380ms cubic-bezier pop 애니메이션으로 체크 아이콘이 등장하며 사용자에게 명확한 피크 순간을 제공한다. 피크-엔드 법칙에서 가장 중요한 "완료" 감정을 올바른 타이밍에 부여하고 있다.

**3. 저장 상태 4단계 (`aria-live`)**
`저장 중 → 저장됨 → 미저장 → 저장 실패`의 4단계와 `aria-live="polite"` 구현은 스크린 리더 사용자를 포함해 항상 문서 상태를 인식할 수 있게 한다.

---

## Priority Issues

### [P0] 도움말 전무 — 위험도 시스템과 기술 용어 미설명

**What**: CRITICAL/HIGH/MEDIUM/confidence 등 핵심 개념에 대한 툴팁·인라인 도움말·온보딩이 전혀 없다. 내보내기 모달의 "Playwright로 카드를 생성하고 있습니다"도 학술 연구자에게 낯선 기술 용어다.

**Why it matters**: 신뢰가 핵심인 학술 논문 처리 도구에서 사용자가 "CRITICAL 필드"의 의미를 모르면 검증 없이 버튼을 누르게 되거나, 반대로 두려워서 이탈한다. Nielsen 10번 heuristic 0점.

**Fix**:
1. CRITICAL/HIGH/MEDIUM 배너에 `?` 아이콘 추가 → hover/click 시 "원문 수치와 AI 추출값이 불일치합니다. 원문을 확인 후 '확인 완료'를 눌러주세요" 설명.
2. confidence 배지에 툴팁: "AI가 이 값을 얼마나 확신하는지를 나타냅니다."
3. 내보내기 렌더링 sub-text에서 "Playwright" 제거 → "고화질 PNG를 생성하고 있습니다."

**Suggested command**: `/impeccable ux-writing`

---

### [P1] Ctrl+S 미지원

**What**: 에디터 환경에서 가장 기대되는 키보드 단축키인 Ctrl+S(또는 Cmd+S)가 없다.

**Why it matters**: 에디터에 익숙한 모든 사용자가 Ctrl+S를 누른다. 자동저장이 있어도 "지금 즉시 저장"에 대한 기대는 여전하다. 아무 반응이 없으면 저장 실패로 오해하거나 불안감을 느낀다.

**Fix**: `attachStaticListeners()`에 `document.addEventListener('keydown', e => { if ((e.ctrlKey || e.metaKey) && e.key === 's') { e.preventDefault(); doSave(); } });` 추가.

**Suggested command**: `/impeccable harden`

---

### [P1] "확인 완료" 단방향 조작 — 취소 불가

**What**: CRITICAL 필드의 "확인 완료" 클릭 시 risk를 null로 설정하고 렌더링하지만, 이를 되돌리는 방법이 없다. 실수로 클릭하거나 재검토가 필요할 경우 방법이 없다.

**Why it matters**: 원문 검증이 핵심 가치인 도구에서 검증 상태를 잘못 처리한 경우 복구 수단이 없다. 사용자 신뢰 훼손 위험.

**Fix**: "확인 완료" 클릭 후 필드에 "다시 검토" 링크 또는 취소 가능한 5초 타이머 토스트 제공. 또는 risk를 null 대신 'confirmed'로 설정해 필드에 "검토 완료" 상태 뱃지를 계속 표시.

**Suggested command**: `/impeccable harden`

---

### [P2] `width` 트랜지션으로 인한 레이아웃 스래시 (자동 감지 확인)

**What**: `.render-fill { transition: width 200ms linear; }` — 진행률 바 width 직접 애니메이션.

**Why it matters**: `width` 변경은 매 프레임 레이아웃 재계산을 강제한다. 3초 렌더링 애니메이션 내내 layout thrash가 발생한다. 저사양 기기에서 jank 유발 가능.

**Fix**: `.render-fill`을 `width: 100%; transform: scaleX(0); transform-origin: left;`로 변경. JS에서 `fill.style.width` 대신 `fill.style.transform = \`scaleX(${pct/100})\`` 로 업데이트.

**Suggested command**: `/impeccable animate`

---

### [P2] 영문 레이블 혼입 ("Image Slot", "Template")

**What**: 디자인 패널 섹션 레이블 "Image Slot"과 콘텐츠 패널 레이블 "Template"이 영문으로 표시된다. 나머지 인터페이스는 전부 한국어다.

**Why it matters**: 언어 전환은 인지 부하를 높이고, 번역이 누락된 것처럼 보여 완성도 인상을 낮춘다.

**Fix**: "Image Slot" → "이미지 슬롯", "Template" → "템플릿". HTML에서 2곳, JS `renderExport()`의 preflight 섹션 레이블은 이미 한국어.

**Suggested command**: `/impeccable ux-writing`

---

## Persona Red Flags

### 학술 연구자 "이수연" (프로젝트 특화 페르소나)

**프로필**: 논문은 자주 쓰지만 SaaS 툴은 익숙하지 않다. 데이터 정확성에 매우 민감하고, 실수가 있으면 논문 신뢰성에 직결된다고 느낀다.

**Primary flow red flags**:
- `confidence: low` 배지가 왜 표시되는지 모른다 → 내용을 신뢰해야 할지 불안해한다.
- "CRITICAL 1건"이 내보내기를 막고 있는데 이유가 배너에 적혀 있지 않다 → "왜 안 되지? 뭘 잘못 한 거지?" 패닉.
- "확인 완료"를 잘못 눌러 CRITICAL을 해제했는데 되돌릴 방법이 없다 → 원문 검증 목적 자체가 무너진다.
- 렌더링 중 "Playwright" 언급 → "이게 뭔지 모르겠는데 내 논문 데이터가 외부에 나가는 건 아닐까?"

### Sam (접근성 의존 사용자)

**Primary flow red flags**:
- CRITICAL/HIGH 위험도 정보가 색상과 텍스트 배지로 이중 제공되어 색각 이상 사용자에게 유리하다 ✅
- 그러나 `img-delete-btn`의 opacity 0 → hover 시 1 동작은 키보드 포커스 시에도 `opacity: 1` 보장됨 ✅
- `aria-live="polite"`로 저장 상태 발표됨 ✅
- **Red flag**: 위험도 뱃지(CRITICAL/HIGH/MEDIUM)의 배경 색상 대비가 WCAG AA 4.5:1을 만족하는지 확인 필요. oklch 팔레트 상 --risk-critical-subtle 위 --risk-critical 텍스트의 구체적 대비율 미검증.
- **Red flag**: 내보내기 모달 PREFLIGHT 체크리스트의 `.preflight-check` 아이콘은 시각적으로만 체크 여부를 전달한다. `aria-label`이나 스크린 리더용 텍스트 대안이 없다.
- **Red flag**: export card button에서 "다운로드" 기능이 아직 미구현이므로 버튼 역할과 실제 동작이 불일치한다.

### Alex (파워 유저)

**Primary flow red flags**:
- Arrow Key로 카드 탭 탐색 가능 ✅
- Esc로 모달 닫기 가능 ✅
- **Red flag**: Ctrl+S 없음 — 에디터 사용자에게 가장 치명적인 누락.
- **Red flag**: 여러 카드의 CRITICAL 필드를 한 번에 모두 확인(배치 처리)하는 방법이 없다. 카드가 10장 이상이면 탭을 하나씩 전환해야 한다.
- **Red flag**: Ctrl+Enter로 내보내기 시작 등 키보드 단축키가 없어 mouse-only 플로우 강제.

---

## Minor Observations

- **썸네일 스트립 스크롤 어포던스 없음**: `scrollbar-width: none`으로 스크롤바가 숨겨져 있어 카드 수가 많을 경우 좌우로 더 있다는 사실을 알 수 없다. 양 끝에 gradient fade mask 처리 권장.
- **`exportClose` 정적 리스너 사문화**: HTML의 `#export-close` 버튼은 첫 `renderExport()` 호출 시 `exportHeader.innerHTML` 교체로 DOM에서 분리된다. `attachStaticListeners()`에서 등록한 `exportClose?.addEventListener('click', closeExport)` 리스너가 실질적으로 동작하지 않는다. 각 phase에서 동적으로 주입하는 `#export-close-btn` 리스너가 실제 동작을 담당한다. 코드 혼선 제거 필요.
- **렌더링 진행률 바 가짜 3초**: 실제 서버 렌더링 시간과 무관한 고정 애니메이션이다. 실제 API 통합 시 서버-sent events 또는 폴링으로 진행률을 연동하지 않으면 100% 도달 후 실제 응답을 기다리는 어색한 UX가 발생한다.
- **미리보기 줌 컨트롤 없음**: 실제 내보내기 해상도는 1080×1080이지만 미리보기는 최대 400px이다. 텍스트 가독성을 실제 크기로 확인할 방법이 없다.
- **확인 완료 버튼의 `risk === 'HIGH'` 조건 재검토**: 현재 구현에서 HIGH 필드도 "확인 완료" 버튼이 표시된다 (`const confirmBtn = (f.risk === 'CRITICAL' || f.risk === 'HIGH')`). 스펙 12번 문서에서 HIGH는 "주의 필요"이지만 확인 완료 처리가 필요한지 명시되지 않았다. UX 정책 확인 필요.

---

## Questions to Consider

- **"CRITICAL 확인 완료를 되돌릴 수 있어야 하는가?"** — 원문 검증 도구의 핵심 신뢰 루프다. '5초 취소 토스트' vs '재-플래그 버튼' 중 무엇이 연구자 워크플로에 더 자연스러운가?
- **"Playwright라는 이름이 사용자에게 가치 있는 정보인가?"** — 렌더링 기술 스택 노출이 신뢰를 주는지, 아니면 불안을 주는지. 학술 연구자에게는 "Playwright" 대신 "고화질 렌더링 엔진"이 더 의미있을 수 있다.
- **"카드가 20장이 넘어가면 어떤 UX가 필요한가?"** — 현재 탭 스트립은 20장 이상에서 스크롤이 길어진다. 카드 그룹핑, 점프 네비게이션, 또는 페이지네이션이 필요한가?
