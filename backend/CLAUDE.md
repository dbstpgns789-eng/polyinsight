# CLAUDE.md — CTO Backend
> PolyInsight 백엔드 | FastAPI + S1-S8 파이프라인 (Python, 포트 8000)
> 선행 읽기: 루트 `../CLAUDE.md` → 이 파일

---

## 세션 시작 필독 (읽기 전 답변 시작 금지)

```
../NORTH_STAR.md              ← 북극성·현재 Phase 확인
../cpo/ROADMAP.md             ← 현재 단계·우선순위
../docs/contracts/04_architecture.md    ← 파이프라인 구조
../docs/contracts/05_agent_design.md    ← Agent 계약·S6 프롬프트
../docs/contracts/07_api_data_model.md  ← API·DB 스키마
ARCHITECTURE.md               ← 로컬 아키텍처 명세
TESTING_HARNESS.md            ← 테스트 기준
agents/deck/AUTHORING.md      ← 저작 자산 컨트롤룸(프롬프트·V·refs·측정) — 저작 관련 작업 시 필독
```

---

## 1. 역할 & 범위

이 디렉토리는 전체 파이프라인을 소유한다.

```
backend/
  agents/       S1·S2·S6·S7·S8 Agent 구현
  core/         Orchestrator, models, run_state
  scripts/      corpus_harness, 유틸리티
  tests/        pytest 스위트 (실행: pytest backend/tests/)
  routers/      FastAPI 라우터
```

---

## 2. S6 Grounding Rules (Most Critical)

S6는 환각에 가장 취약한 stage다.

```
RULE 1: section_map(원문)이 유일한 사실 소스
RULE 2: S3/S4 출력은 힌트 — 원문과 충돌하면 원문 우선
RULE 3: 모든 수치는 반드시 {section, page} 출처 포함
RULE 4: 원문에 없는 내용 추가 금지
RULE 5: grounding 증명 불가 → low confidence로 표면화
```

S6 JSON 각 필드 필수 구조:
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

**Risk 분류 (수치에만 HIGH/CRITICAL 적용)**:
```
quantitative + failed              → CRITICAL
quantitative + (fuzzy|semantic)    → HIGH
quantitative + normalized          → MEDIUM
qualitative|causal + any           → MEDIUM (상한)
exact match                        → LOW
```

---

## 3. Stage Contract Discipline

각 stage는 엄격한 경계로 취급한다.

금지:
- raw LLM 출력을 다음 stage에 검증 없이 전달
- "응답이 맞아 보여서" schema 검증 스킵
- upstream 실패를 downstream에서 패치로 보상
- 비정상 입력을 정상처럼 보이게 은닉

stage가 degraded면 → RunState와 output status에 명시적으로 표면화.

---

## 4. Degraded Mode Rules

Degraded mode ≠ success.

degraded_mode 트리거 시:
- 출력을 정상 품질처럼 제시 금지
- degraded 상태를 RunState.warnings에 보존
- final status에 품질 저하 반영
- 임의 텍스트 분할로 section-level confidence 조작 금지

---

## 5. 테스트 실행

```bash
# 반드시 경로 명시
pytest backend/tests/

# bare pytest 금지 — pytest.ini가 가리키는 죽은 tests/unit/ 실행됨
```

---

## 6. 실호출 비용 규칙

LLM 실 API 호출(S6 gate ab/full, 풀런 등)은 **실행 전 반드시 허락 받는다**.
mock/단위 테스트는 예외.

★로컬 개발 기본값 = `DEV_MOCK_LLM=True`(mock, 비용0). 실호출(`=False`)로 전환은 **사용자 허락 필수** — 편집·캡션·저작 로컬 테스트도 `=False`면 실제 과금된다. (2026-07-22: 로컬이 `=False`라 그냥 테스트가 조용히 Sonnet 과금된 구멍 → 환경 기본값으로 규칙 강제.)

---

## 7. NEVER (Backend 전용)

```
NEVER  bare pytest — 반드시 pytest backend/tests/ 지정
NEVER  실 LLM 호출 전 비용 확인 생략
NEVER  에러 처리 선코딩 — 실 논문 돌린 에러 보고 후 대응
NEVER  raw logging 없이 실호출 — 에러 재현 불가
NEVER  uvicorn 재시작 없이 코드 변경 후 테스트
NEVER  S6 출력 수치를 원문 확인 없이 그냥 통과
NEVER  프롬프트/V/refs 변경 커밋에 agents/deck/AUTHORING.md §2 결정로그 누락
NEVER  측정(eval 베이스라인) 없이 프롬프트 품질 변화를 "좋아졌다"고 주장
```

---

## ⚠️ Learned Mistakes
> 실전에서 발생한 치명적 실수. 세션 중 즉시 추가. 절대 삭제 안 함.

| 날짜 | 상황 | 실수 | 규칙 |
|------|------|------|------|
| 2026-06-XX | 테스트 실행 | bare `pytest` → 죽은 tests/unit/ 스위트 실행, 119개 실패처럼 보임 | 항상 `pytest backend/tests/` 경로 명시 |
| 2026-06-XX | S6 에러처리 | 실 논문 실행 전에 방어 코드 선작성 → 실제 에러 패턴 못 잡고 러닝 막음 | 실 논문 돌려 난 에러를 보고 고친다. raw 로깅 필수 |
| 2026-06-XX | 개발 루프 | 코드 변경 후 uvicorn 재시작 안 함 → 이전 코드 계속 실행 | 코드 변경 시 uvicorn 수동 재시작 필수 |
