---
timestamp: 2026-05-19T01-48-32Z
slug: src-pages-editor-jobid-astro
---
## Design Health Score

| # | Heuristic | Score | Delta | Key Issue |
|---|-----------|-------|-------|-----------|
| 1 | Visibility of System Status | 4 | — | 저장·위험도·진행률 모두 구현됨 |
| 2 | Match System / Real World | 4 | ▲+1 | 영문 레이블 전부 한국어화, Playwright 제거 완료 |
| 3 | User Control and Freedom | 3 | — | 확인 완료 5초 undo 추가됨, 그러나 Ctrl+Z 에디팅 히스토리 미지원 |
| 4 | Consistency and Standards | 3 | — | 디자인 시스템 일관적 |
| 5 | Error Prevention | 3 | — | CRITICAL 차단·자동저장 탄탄 |
| 6 | Recognition Rather Than Recall | 3 | — | 위험도 이중 노출 우수, 썸네일 스크롤 어포던스 미제공 |
| 7 | Flexibility and Efficiency of Use | 3 | ▲+1 | Ctrl+S 추가, Arrow키 유지, 배치 작업 없음 |
| 8 | Aesthetic and Minimalist Design | 4 | — | 불필요 장식 없음 |
| 9 | Help Users Recover from Errors | 2 | — | 내보내기 재시도 구현, 저장 실패 원인 미제공 |
| 10 | Help and Documentation | 2 | ▲+2 | CRITICAL/HIGH/confidence 인라인 툴팁 추가됨, 온보딩·전문 도움말 없음 |
| **Total** | | **31/40** | **▲+4** | **Good — 기반 견고, 약한 영역 개선 권장** |

---

## Anti-Patterns Verdict

**AI 슬롭 판정: Negative (이전과 동일).**

자동화 스캐너 결과: **0건** (이전 1건 → 0건).
- 이전 플래그된 `layout-transition` (`.render-fill transition: width`) → `transform: scaleX()` 교체로 해결됨.

---

## Score Improvement Summary

| 항목 | 이전 (27/40) | 현재 (31/40) | 변화 원인 |
|------|------------|------------|---------|
| Match System/Real World | 3 | 4 | "Template"·"Image Slot" 한국어화, "Playwright" 제거 |
| Flexibility/Efficiency | 2 | 3 | Ctrl+S 단축키 추가 |
| Help & Documentation | 0 | 2 | CRITICAL/HIGH/confidence 인라인 툴팁 |
| Anti-pattern scan | 1건 | 0건 | render-fill layout thrash → GPU transform |

---

## 잔여 주요 이슈

- **[P1] `.help-icon` 키보드 포커스 아웃라인 없음**: `opacity` 변화로만 포커스를 표시하여 WCAG 2.4.7 위반.
- **[P1] `.done-card-btn` accessible label 없음**: "01" / "02" 텍스트만으로는 스크린 리더 사용자가 다운로드 대상을 알 수 없음.
- **[P2] 저장 실패 원인 미제공**: "저장 실패" 상태에서 원인 메시지 없음.
- **[P3] 썸네일 스크롤 어포던스**: 카드 다수 시 overflow 시각적 힌트 없음.
