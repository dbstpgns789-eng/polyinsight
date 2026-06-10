# Risk 분류 정직화 — 의역은 위험 아니다 (A)

> PolyInsight | 2026-06-06 | S6 grounding 계약 변경
> 상태: 결정, 구현

## Problem
S6 `_post_process`의 risk 판정이 **claim_type 무관하게** `match_quality ∈ {fuzzy, semantic}`이면 HIGH로 매긴다. 그래서 **정성 문장의 의역**(쉽게 풀어쓴 본문)이 대거 HIGH로 잡힌다. 실제 Transformer 논문 출력에서 수치(28.4 BLEU 등)는 exact=LOW로 정확한데, 의역 문장 다수가 HIGH가 됐다.

증상:
- export 프리플라이트 경고가 시끄럽다(멀쩡한 카드에 "미검토 N·정합성 불일치").
- FactDrawer·LeftPanel의 CRITICAL/HIGH 건수가 부풀려져 신뢰가 떨어진다("늑대야").
- (참고) export는 **실제로 막히지 않는다** — Topbar 버튼·ExportModal "내보내기 시작" 모두 disabled 없음. CLAUDE.md §8의 "CTA 비활성"은 미구현 상태였다. 즉 차단 버그가 아니라 **라벨 노이즈** 문제.

## Decision
**위험 신호는 수치(정량)가 진다. 정성/인과 의역은 HIGH/CRITICAL이 될 수 없고 MEDIUM이 상한이다.**

새 `_post_process` 규칙:
```
정량(quantitative) + failed              → CRITICAL
정량 + (fuzzy|semantic)                   → HIGH
정량 + normalized                         → MEDIUM
정성/인과(qualitative|causal) + (failed|fuzzy|semantic) → MEDIUM (상한)
그 외(exact, 정성 normalized 등)          → LOW
```

그리고 CLAUDE.md §8을 **현실+철학에 맞게** 수정: export는 하드 차단이 아니라 **프리플라이트 경고 + 사용자 최종 판단**(제품 원칙 "최종 판단은 사용자가"와 정합). "CTA 비활성"은 폐기.

## Rationale
- moat = 수치 정확성. 의역은 [[project-readability-failure]]에서 "fidelity 위반 아님"으로 이미 합의 — 쉽게 풀기는 권장사항이지 위험이 아니다.
- 위험을 수치에 집중시키면 CRITICAL/HIGH가 **진짜 신경 쓸 것(미검증 숫자)** 만 가리켜 검증 UX가 의미를 회복한다.
- export 비차단은 이미 코드 현실이자 "사용자 통제" 철학과 맞다 — 문서를 코드/철학에 맞춘다(CLAUDE.md §9).

## Risks / 주의
- 정성 의역이 MEDIUM으로 남으므로 "검토 권장" 신호는 유지(완전 무음 아님).
- 정량 + semantic을 HIGH로 유지 → 약하게 매칭된 *숫자*는 여전히 경고(환각 방지).
- 계약 변경: CLAUDE.md §3(risk 정의)·§8(게이트) 갱신. 프론트 RiskLevel 타입은 이미 MEDIUM 포함 — 변경 불요.

## 변경 범위
- `backend/agents/s6_card_json.py` `_post_process` (규칙).
- `CLAUDE.md` §3(taxonomy 한 줄 추가)·§8(게이트 문구)·§11(changelog).
- `backend/tests/test_s6_skeletons.py` `_post_process` 직접 단위테스트 추가.
- 프론트·데이터모델 불변.
