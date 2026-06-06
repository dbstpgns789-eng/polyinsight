# CLAUDE.md
> PolyInsight v2.0 | 2025-05-05
> This file is the execution protocol for Claude Code in this repository.
> Treat every rule here as mandatory, not optional guidance.
> This file will be updated as design decisions evolve.

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

## 2. Pipeline Structure (v2.0 — Current)

```
S1  Text Extraction     pdfplumber / PyMuPDF
S2  Section Parsing     regex + LLM fallback
  ↓
S6  Card News JSON      원문 direct read + 내부 chain-of-thought으로 기여/요약 추출
S7  PNG Rendering       Playwright (NOT Pillow)
S8  Output Packaging    SQLite persistence
```

**Breaking changes from v1.0:**
- S3/S4 are **removed** — absorbed into S6 chain-of-thought
- S5 (Promotional Sentences) is **removed** from KITECH pipeline
- S6 treats the source text as primary — internal reasoning only
- S7 uses **Playwright** screenshot, not Pillow template renderer
- Storage is **SQLite** (permanent), not in-memory dict (TTL 30min)

---

## 3. S6 Grounding Rules (Most Critical)

S6 is the stage most vulnerable to hallucination.
These rules are non-negotiable:

```
RULE 1: section_map (source text) is the ONLY source of facts
RULE 2: S3/S4 outputs are hints — if they conflict with source, source wins
RULE 3: Every numeric value MUST include source field: {section, page}
RULE 4: Never add content not present in the source paper
RULE 5: If grounding cannot be demonstrated, surface it as low confidence
```

Each field in S6 JSON output must carry:
```json
{
  "value": "...",
  "confidence": "high|medium|low",
  "match_quality": "exact|normalized|fuzzy|semantic|failed",
  "claim_type": "quantitative|qualitative|causal",
  "source": { "section": "Results", "page": 7 },
  "risk_level": "CRITICAL|HIGH|MEDIUM|LOW"
}
```

CRITICAL = quantitative + match_quality failed → always flag for human review.

**Risk escalates only on NUMBERS (claim_type = quantitative).** Qualitative/causal
paraphrase caps at MEDIUM — rewriting prose for readability is not a fidelity risk.
```
quantitative + failed              → CRITICAL
quantitative + (fuzzy|semantic)    → HIGH
quantitative + normalized          → MEDIUM
qualitative|causal + (failed|fuzzy|semantic) → MEDIUM  (cap)
else (exact, qualitative normalized)         → LOW
```

---

## 4. Architecture Invariants

These structural rules do not change without explicit decision:

- The Orchestrator is the **only controller** of pipeline execution
- Agents do not call each other directly
- Each stage receives **validated input** and returns **typed output**
- S8 always runs, even when upstream stages fail
- S5 does not exist in this pipeline
- S3 and S4 do not exist in this pipeline

---

## 5. Stage Contract Discipline

Treat each stage as a strict boundary.

Do not:
- pass raw LLM output to the next stage without validation
- skip schema validation because a response "looks correct"
- patch downstream stages to compensate for upstream failures
- hide degraded inputs behind normal-looking outputs

If a stage is degraded, surface it explicitly in RunState and output status.

---

## 6. Degraded Mode Rules

Degraded mode ≠ success.

When degraded_mode triggers:
- do not silently present outputs as normal quality
- preserve degraded state in RunState.warnings
- reflect degraded quality in final status
- do not fabricate section-level confidence from arbitrary text splitting

---

## 7. What Never to Do

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

## 8. Frontend Screen Structure

```
/dashboard          Project list, stats, activity feed
/editor/:jobId      3-panel card editor (Content | Preview | Design)
upload modal        Upload & processing overlay (no separate route)
export modal        Export & download overlay (no separate route)
```

Key frontend rules:
- Upload and Export are **modals** (React Portal), not pages
- Export preflight **warns** on unreviewed/CRITICAL items but does **not** hard-block —
  user has final judgment ("최종 판단은 사용자가"). (Earlier "CTA disabled on CRITICAL/HIGH"
  was never implemented and is retired by decision 2026-06-06.)
- Image slots are **optional** — export is allowed without images
- Auto-save every 5 seconds idle

---

## 9. Source of Truth for Decisions

Before changing code, always read:

```
docs/04_architecture.md   Pipeline structure and component design
docs/05_agent_design.md   Agent contracts and S6 prompt rules
docs/07_api_data_model.md API endpoints and data schemas
```

If code conflicts with docs → treat docs as intended design.
Note the mismatch explicitly before fixing.

---

## 10. Working Style

When making changes:
- **one task = one change** — do not combine unrelated changes
- prefer minimal changes that preserve stage contracts
- keep fixes local to the responsible stage
- if a bug exposes a spec mismatch, note both the fix and the drift
- commit format: `[S1-S8 | FE | BE | DOCS] brief description`

When writing docs:
- write in technical, decision-oriented tone
- prefer sections: Problem / Decision / Rationale / Risks
- document trade-offs explicitly
- avoid long tutorials

---

## 12. Monorepo Structure (v2.2 — Current)

```
polyinsight/
  CLAUDE.md          ← 모든 Claude가 읽는 공통 규칙 (이 파일)
  PRODUCT.md         ← 브랜드/제품 정의 (impeccable 스킬 참조)
  DESIGN.md          ← 디자인 시스템 토큰 (impeccable 스킬 참조)
  package.json       ← npm workspaces 루트
  docs/              ← canonical 공유 문서 — 복사본 생성 금지
  backend/           ← FastAPI + S1-S8 파이프라인 (Python, 포트 8000)
  web/               ← Next.js 15 프로덕션 프론트엔드 (포트 3000)
    CLAUDE.md        ← web 전용 추가 규칙
```

**포트 할당 (충돌 없음)**:
- `backend`: 8000 (FastAPI uvicorn)
- `web`:     3000 (Next.js dev server)

**각 Claude 역할별 필수 읽기 파일**:

| Claude 역할 | 필수 파일 |
|---|---|
| 모든 Claude | 루트 `CLAUDE.md` |
| Backend/Full-stack | `docs/04_architecture.md`, `docs/07_api_data_model.md` |
| Web Claude | `web/CLAUDE.md`, `docs/10_screen_design.md`, `docs/12_card_editor_content.md` |

**docs/ 원칙**: 파일 하나, 위치 하나. 각 workspace에 복사본 생성 금지.
docs 변경 → 코드 변경 순서를 지킨다.

---

## 11. Change Log

| Date       | Version | Change Summary                                              |
|------------|---------|-------------------------------------------------------------|
| 2026-06-06 | v2.3    | risk 분류 정직화 (정량만 HIGH/CRITICAL, 정성 의역 MEDIUM 상한) + export는 경고-후-진행(하드 차단 폐기). docs/superpowers/specs/2026-06-06-risk-taxonomy-design.md |
| 2026-05-19 | v2.2    | frontend/, landing/ 삭제 (deprecated 프로토타입), web/ 단독 프론트엔드로 확정, PRODUCT.md/DESIGN.md 루트로 이동 |
| 2026-05-19 | v2.1    | Monorepo 통합 (landing/, web/ 추가), CSS 이식 실패 회고 → web/CLAUDE.md 규칙 추가 |
| 2025-05-05 | v2.0    | S3/S4 removed (absorbed into S6), S5 removed, Playwright, SQLite, S6 rewrite |
| (previous) | v1.0    | Sequential S1-S8, Pillow, in-memory dict, S5 included       |

## 13. CSS 이식 공통 규칙

복수의 CSS 시스템을 하나로 합칠 때 발생하는 토큰 불일치 방지 규칙.
`web/CLAUDE.md` 섹션 6에서 구체적 매핑 테이블 확인.

**핵심 원칙**: 이식(코드 옮기기) 전에 통합(디자인 언어 통일)이 선행되어야 한다.

```
NEVER  @theme 블록에 hex/rgb 색상값을 직접 쓴다 — 반드시 var() 참조
NEVER  "빌드 성공"을 이식 완료 기준으로 삼는다
ALWAYS 이식 전 토큰 매핑 테이블을 작성한다
ALWAYS 이식 후 브라우저에서 두 영역의 색상이 동일한지 시각 검증한다
```

자세한 사례 분석: `docs/14_migration_retrospective.md`
