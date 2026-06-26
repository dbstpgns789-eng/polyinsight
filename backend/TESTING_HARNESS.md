# TESTING_HARNESS.md — 테스트 하네스 명세

> 파이프라인 회귀를 막는 검증 체계.
> 코퍼스 하네스 + 단위 테스트 + 불변식 체계를 정의한다.

---

## 테스트 스위트 구조

```
backend/tests/
    unit/          S1·S2·S6 단위 테스트
    integration/   Orchestrator E2E 테스트
    corpus/        코퍼스 하네스 (별도 스크립트)

실행: pytest backend/tests/    ← 경로 명시 필수
     bare pytest 금지 — 죽은 tests/unit/ 실행됨
```

---

## 코퍼스 하네스 (corpus_harness)

### 목적

85편 논문을 S1 → S2까지 배치 실행하여 파이프라인 견고성 검증.
LLM 호출 없음 (S1/S2만).

### 실행

```bash
python -m backend.scripts.corpus_harness --stage s1 --corpus <경로>
python -m backend.scripts.corpus_harness --stage s1 --corpus <경로> --seq  # 순차 모드
```

### 리포트 형식

```
=== S1 견고성 리포트 (N편) ===
code별: s1_no_sections N / 정상 M

s1_no_sections × input_profile (핀셋 대상):
  columns=2 · journal=other:10.XXXX : K편
  예: 논문명.pdf
```

### 성공 기준

| 지표 | 목표 |
|------|------|
| S1 추출 성공률 | > 98% (85편 중 83편 이상) |
| s1_no_sections 비율 | < 5% |
| 실행 시간 (85편) | < 10분 |

---

## Golden 세트

### Golden 8 (핵심)

8편의 대표 논문 — 도메인·포맷·언어 다양성 보장.
S6 출력 품질 기준 논문으로 사용.

선정 기준:
- 다양한 도메인 (med/chem/mat/eng/...)
- 1컬럼 + 2컬럼 혼합
- 한국어 논문 1편 이상
- 수치가 풍부한 Results 섹션 포함

### Golden 22 (확장, 예정)

22편으로 확장 — 엣지케이스 포함 (bioRxiv preprint, 한국어 저널, 수식 중심 논문 등).

---

## 4층 불변식 (Invariants)

S6 출력에 대해 항상 검증하는 조건:

### Tier 1: 스키마 (최강)
- 모든 CardData 필드에 `source.section` + `source.page` 존재
- `risk_level` 값은 CRITICAL|HIGH|MEDIUM|LOW 중 하나
- `confidence` 값은 high|medium|low 중 하나

### Tier 2: Grounding
- quantitative claim → match_quality != "failed" 이거나 risk_level = "CRITICAL"
- CRITICAL 항목은 human_review_required = True

### Tier 3: 밀도
- 카드 1장 본문 글자수: 60~200자 (한국어 기준)
- headline: 10~40자
- 카드 총 수: 3~7장

### Tier 4: 중복
- Jaccard 유사도 기반 카드간 중복 검사
- 동일 카드 내 headline ↔ body 중복 > 0.7 → 경고

---

## 회귀 방지 규칙

| 변경 사항 | 필수 검증 |
|-----------|-----------|
| S1 파서 수정 | corpus_harness 85편 재실행 |
| S6 프롬프트 수정 | Golden 8 세트 재검증 |
| 스키마 변경 | 4층 불변식 전체 통과 |
| 새 템플릿 추가 | S7 PNG 렌더 시각 검증 |

---

## 비용 주의

S6 실 LLM 호출 테스트 = 비용 발생.
실행 전 반드시 허락 받을 것.

```
Haiku:  ~$0.01/편
Sonnet: ~$0.03/편 (멀티에이전트 Architect)
85편 풀런 예상: ~$1.00
```
