# CLAUDE.md — CEO (전사 절대원칙)
> PolyInsight | 루트에서 Claude를 열면 전사 컨텍스트.
> 모든 부서(CPO·CTO·COO·CMO)가 공유하는 절대 원칙.

## 부서 구조

| 부서 | 폴더 | 담당 |
|---|---|---|
| CEO | `/` (루트) | 전사 원칙·비전·최종 결정 |
| CPO | `cpo/` | 제품 기획·로드맵·ROI |
| CTO | `backend/` `web/` | 코드 소유 (파이프라인·API·프론트 구현) |
| CDO | `cdo/` | 디자인 스펙 소유 (시스템·컴포넌트 명세·UX 결정) |
| COO | `coo/` | 운영·서버·DB·회원·비용 |
| CMO | `cmo/` | 마케팅·채널·클릭률·SNS |

> 부서 세션 시작 시 해당 폴더에서 Claude를 연다.
> 부서간 핸드오프는 `docs/`를 경유한다.

---

## 1. What This Project Is

PolyInsight converts academic paper PDFs into
**KITECH-style card news (5 × 1080×1080 PNG)**.

Core principle — **fidelity over style**:
- Every output must be traceable to the source paper
- Do not introduce claims not supported by the source
- Numbers and statistics must be quoted directly from the original text

Design philosophy (v3.0 — Authoring Inversion):
- **창작은 AI가** — 스토리·**형태(레이아웃) 발명**·표현을 AI가 **한 마음에서 동시에 저작**한다.
  코드는 형태를 미리 규정하지 않는다 (고정 카탈로그·필드 스키마로 가두지 않는다).
- **검증은 코드가** — 수치·팩트의 원문 대조는 코드가 전담한다 (**이것이 해자**).
- **최종 판단은 사용자가** — 사용자는 검토·수정·승인 권한을 가진다.

> 2026-06-28 교훈: 이전 구현은 창작을 **코드가**(30 카탈로그·architect/writer 분리·경직 필드포맷)
> 했다 — §1 위반. 형태와 내용을 가르면 '형태=내용'인 카드([MASK] 빈칸 체험형)는 구조적으로
> 불가능하다. Opus를 넣어도 "넌 형태 정하지 마/넌 글 쓰지 마" 프롬프트에선 안 빛난다.
> 레퍼런스(output/cardnews_*)가 빛난 건 한 마음이 이해→형태→표현을 한 번에 저작했기 때문.

---

## 2. Pipeline Structure (v3.0 — Authoring Inversion)

```
S1  Text Extraction   pdfplumber / PyMuPDF
  ↓
S6  Deck Authoring     강한 모델이 덱 전체를 한 번에 저작 — 스토리+형태+표현.
                       형태를 카탈로그에서 고르지 않고 내용에 맞게 발명. 출력=렌더 가능 구조.
  ↓
V   Fidelity Verify    코드가 저작물의 모든 수치를 원문과 대조 (해자). 미확인은 사용자에 표면화.
  ↓
S7  Render             Playwright — 저작된 구조를 렌더 (NOT Pillow)
S8  Output Packaging   SQLite persistence
```

**Breaking changes from v2.0:**
- S6 **architect/writer 분리 폐기** — 이해와 표현을 가르는 칙령이 '형태=내용' 카드를 불가능하게 함.
- 30 레이아웃 카탈로그 = **선택 강제(감옥) → 선택적 팔레트로 강등.** 모델이 형태를 발명 가능.
- **V(검증) 단계 명시** — 자유 저작 + 코드 사후 검증 = 헌법 1조의 정확한 구현.
- 편집 = 저작된 구조 위 **WYSIWYG** (고정 필드 스키마 편집 폐기 방향).

> 가설 증명 후 backend/ 구현. S6 세부 규칙 → `backend/CLAUDE.md`

---

## 3. Architecture Invariants

변경하려면 명시적 결정 필요:

- Orchestrator는 **유일한 파이프라인 컨트롤러**
- Agent끼리 직접 호출 금지 — Orchestrator 경유만
- 각 stage는 **validated input** 수신 → **typed output** 반환
- S8은 upstream 실패 시에도 항상 실행
- S3, S4, S5는 이 파이프라인에 존재하지 않음

---

## 4. Working Style

- **one task = one change** — 무관한 변경 동시 금지
- stage contract를 보존하는 최소 변경 우선
- bug fix는 해당 stage에만 국한
- spec 불일치 발견 시 → 불일치 먼저 명시, 그 다음 fix
- commit format: `[S1-S8 | FE | BE | DOCS] brief description`
- docs 변경 → 코드 변경 순서 엄수

---

## 5. Monorepo Structure (v2.4)

```
polyinsight/
  CLAUDE.md          ← 전사 규칙 (이 파일)
  NORTH_STAR.md      ← 북극성 지표 + ROI 목표
  WORKFLOW.md        ← 부서간 핸드오프 컨트랙트
  PRODUCT.md         ← 브랜드/제품 정의
  DESIGN.md          ← 디자인 시스템 토큰
  package.json       ← npm workspaces 루트
  docs/              ← canonical 공유 문서 — 복사본 생성 금지
  cpo/
    CLAUDE.md        ← CPO 역할 규칙
    PRD.md           ← 제품 요구사항 정의서
    ROADMAP.md       ← 마일스톤 + 연기 목록
  cdo/
    CLAUDE.md        ← CDO 역할 규칙 (디자인 + 프론트엔드)
    DESIGN_SYSTEM.md ← 브랜드 시각적 정체성 + 토큰
    UI_COMPONENTS.md ← 컴포넌트 명세
  backend/
    CLAUDE.md        ← CTO 백엔드 규칙 (S6·stage contract·degrade)
    ARCHITECTURE.md  ← 파이프라인 + DB 스키마
    TESTING_HARNESS.md ← 코퍼스 하네스 + 불변식
  web/
    CLAUDE.md        ← Next.js 구현 규칙 (화면구조·CSS)
  cmo/
    CLAUDE.md        ← CMO 역할 규칙
    COPYWRITING_GUIDE.md ← 톤앤매너 + 카피 원칙
    GTM_STRATEGY.md  ← 시장 진출 전략
  coo/
    CLAUDE.md        ← COO 역할 규칙 (운영·서버·비용)
```

**포트 할당**: `backend` 8000 / `web` 3000

**각 역할별 필수 읽기**:

| 역할 | 필수 파일 |
|---|---|
| 모든 Claude | 루트 `CLAUDE.md` |
| Backend | `backend/CLAUDE.md`, `docs/contracts/04_architecture.md`, `docs/contracts/07_api_data_model.md` |
| Web | `web/CLAUDE.md`, `docs/contracts/10_screen_design.md`, `docs/contracts/12_card_editor_content.md`, `docs/contracts/18_card_design_system.md` |

---

## 6. Source of Truth

코드 변경 전 항상 읽어야 할 파일:
```
docs/contracts/04_architecture.md        Pipeline structure
docs/contracts/05_agent_design.md        Agent contracts + S6 prompt rules
docs/contracts/07_api_data_model.md      API endpoints + data schemas
docs/contracts/18_card_design_system.md  Card skin/skeleton, tokens, focal/image_fit
```
코드 ↔ docs 충돌 → **docs가 의도된 설계**. 불일치를 명시 후 수정.

---

## 7. NEVER

```
NEVER  cage AI authoring in a fixed schema/catalog when the content needs a new form (§1)
NEVER  sever comprehension from expression — the mind that decides form must also write content
NEVER  change stage contracts without updating docs/ first
NEVER  treat derived summaries as more authoritative than source text
NEVER  emit numeric statements without source reference
NEVER  label output as verified unless the code actually proves it (이것이 해자)
NEVER  skip docs/ update before code change
```

> 폐기된 NEVER (v2.0 → v3.0): "invent fields not in schema", "merge multiple stages"
> — §1 창작 권한과 모순돼 폐기. 형태 발명·창작 통합은 이제 권장.

---

## 8. Change Log

| Date | Version | Summary |
|------|---------|---------|
| 2026-06-28 | v3.0 | **Authoring Inversion** — 창작을 AI에 환원(형태 발명 권한), architect/writer 분리·카탈로그 감옥·필드스키마 폐기, V(검증) 단계 명시. 레퍼런스 벤치마크가 노출한 §1 위반 시정. 해자=수치검증·편집·브랜드 |
| 2026-06-26 | v2.4 | CLAUDE.md 부서별 분리 (root=CEO only, backend/web 전용 파일 신설) |
| 2026-06-06 | v2.3 | risk 분류 정직화 + export 경고-후-진행(하드블록 폐기) |
| 2026-05-19 | v2.2 | web/ 단독 프론트엔드 확정, PRODUCT.md/DESIGN.md 루트 이동 |
| 2026-05-19 | v2.1 | Monorepo 통합, CSS 이식 실패 회고 |
| 2025-05-05 | v2.0 | S3/S4/S5 removed, Playwright, SQLite |

---

## ⚠️ Learned Mistakes
> 실전에서 발생한 치명적 실수. 세션 중 즉시 추가. 절대 삭제 안 함.

| 날짜 | 상황 | 실수 | 규칙 |
|------|------|------|------|
| 2025-05-05 | S6 리팩터 | S3/S4를 S6에 암묵 병합 → stage contract 파괴 | stage 합병은 docs 결정 후에만. 암묵 흡수 금지 |
| 2026-05-19 | CSS 이식 | frontend/ hex 토큰을 web/ OKLCH에 직접 복사 → 브랜드 색 불일치 | 이식 전 토큰 매핑 테이블 필수. 완료 기준 = 시각 검증 |
| 2026-06-06 | Export UX | CRITICAL 리스크 항목 CTA 하드블록 구현 → 사용자 판단권 침해 | export는 경고 후 진행. 하드블록 없음. 최종 판단은 사용자 |
| 2026-06-11 | 성능 최적화 | ROI 검증 없이 프롬프트 캐싱 구조 선설계 → 프리픽스 제약으로 폐기 | 비용 최적화는 실측 후. 선제 구조 변경 금지 |
| 2026-06-26 | 다중 문서 동시 작성 | 병렬 작성 시 문서 간 cross-check 없이 commit → 역할 충돌·누락 다수 | 다중 문서 작성 후 반드시 상호 일관성 검증. 뼈대 ≠ 완성 |
| 2026-06-26 | CMO 문서 작성 | docs/19·20·PRODUCT.md 읽기 전에 "인용수/H-index" 프레임 발명 → 확립된 컨텍스트 덮어씀 | 부서 문서 작성 전 해당 도메인의 기존 docs/ 전부 읽기. 발명 금지 |
| 2026-06-28 | 레퍼런스 벤치마크 | 우리 파이프라인이 창작을 코드(카탈로그·architect/writer분리)가 하게 만듦 → §1 위반. 단일 에이전트가 논문만으로 발행급 뽑아 압도 | 창작은 AI가 한 마음에 저작. 코드는 형태 안 가둠. 모델 탓 전에 "프롬프트가 빛나는 행위를 금지했나" 먼저 본다 |
| 2026-07-09 | 저작 역전 후 문서 방치 | 헌법 v3.0(6-28)이 architect/writer 폐기·코드는 `agents/deck/`로 감. 근데 계약문서 04·05를 안 고침 → **11일간 문서가 삭제 예정 코드를 정본 S6로 서술**. L0 착수 때 발굴. 애자일하게 코드만 나가고 문서 앵커·전환 기록 안 남김 | **"docs 먼저"는 신기능뿐 아니라 폐기/전환에도 적용.** 경로 갈아탈 때 구 경로 계약문서 즉시 은퇴 표시. 애자일해도 전환 기록(배너·changelog)은 그 자리에 남긴다. 코드↔docs 표류 = 되돌아볼 때 꼬임의 뿌리 |
| 2026-07-13 | **의존성이 끊긴 상수** | `MAX_SOURCE_CHARS=60000`은 **refs 2개(40KB)가 입력에 함께 들어가서** 정한 값이었다(주석에 이유가 명시돼 있었다). 그런데 ①모델이 Sonnet→Opus로 격상되고 ②refs를 은퇴(12k 토큰이 비었)시키고도 **상한을 재검토하지 않았다.** 결과: chitosan 논문의 **결론이 175자 차이로 잘림**. 게다가 나는 그 주석을 읽고도 연결 못 하고 "참고문헌 제거"로 **우회**했다 — 증상을 치료하고 병인을 놔뒀다. Opus 컨텍스트는 200k 토큰이라 20만 자 논문도 68%밖에 안 쓴다 | **결정 A 때문에 정한 값 B는, A를 폐기할 때 함께 재검토한다.** 상수의 주석에 "왜"가 적혀 있으면 그 "왜"가 아직 유효한지 먼저 확인하라. 그리고 **물려받은 가정을 의심하라** — 오늘만 3번 당했다(refs가 마감을 담보한다 / 중첩 div는 못 자른다 / 60k가 상한이다 — 전부 근거 없었다) |
