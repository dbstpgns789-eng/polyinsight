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

Design philosophy:
- **창작은 AI가** — 스토리 기획, 템플릿 선택, 레이아웃 결정은 AI의 책임이다
- **검증은 코드가** — 수치와 팩트의 원문 대조는 코드가 전담한다
- **최종 판단은 사용자가** — 사용자는 검토·수정·승인 권한을 가진다

---

## 2. Pipeline Structure (v2.0)

```
S1  Text Extraction     pdfplumber / PyMuPDF
S2  Section Parsing     regex + LLM fallback
  ↓
S6  Card News JSON      원문 direct read + chain-of-thought으로 기여/요약 추출
S7  PNG Rendering       Playwright (NOT Pillow)
S8  Output Packaging    SQLite persistence
```

**Breaking changes from v1.0:**
- S3/S4 **removed** — absorbed into S6 chain-of-thought
- S5 **removed** — Promotional Sentences 단계 폐기
- S7 uses **Playwright** screenshot (NOT Pillow)
- Storage is **SQLite** (permanent), not in-memory dict (TTL 30min)

> S6 세부 규칙 → `backend/CLAUDE.md`

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
NEVER  invent fields not in the defined schema
NEVER  change stage contracts without updating docs/ first
NEVER  merge multiple stages to take a shortcut
NEVER  add cross-stage dependencies outside the Orchestrator
NEVER  treat derived summaries as more authoritative than source text
NEVER  emit numeric statements in S6 without source reference
NEVER  label output as verified unless the code actually proves it
NEVER  skip docs/ update before code change
```

---

## 8. Change Log

| Date | Version | Summary |
|------|---------|---------|
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
