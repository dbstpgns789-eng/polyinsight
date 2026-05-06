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
- Card editor ActionBar CTA is **disabled** when CRITICAL/HIGH count > 0
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

## 11. Change Log

| Date       | Version | Change Summary                                              |
|------------|---------|-------------------------------------------------------------|
| 2025-05-05 | v2.0    | S3/S4 removed (absorbed into S6), S5 removed, Playwright, SQLite, S6 rewrite |
| (previous) | v1.0    | Sequential S1-S8, Pillow, in-memory dict, S5 included       |
