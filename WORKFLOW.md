# WORKFLOW.md — 부서간 결재 라인 & 핸드오프 컨트랙트

> 이 문서는 데이터·결정·산출물이 부서간 어떻게 이동하는지를 정의한다.
> 어느 부서가 무엇을 먼저 확정해야 다음 부서가 움직일 수 있는지를 못 박는다.

---

## 결재 라인 (순서 엄수)

```
CEO (NORTH_STAR)
    ↓ 전사 방향 확정
CPO (PRD + ROADMAP)
    ↓ 제품 요구사항 확정
    ├──→ CTO: DB 스키마 + API 계약 설계
    └──→ CDO: 화면 구조 + 컴포넌트 명세 설계
           ↓ (CTO API 계약 확정 후)
         CDO: 실제 프론트 구현
           ↓ (CDO 템플릿 확정 후)
         CTO: S7 렌더 파이프라인 연동
    ↓
CMO: GTM + 카피라이팅
COO: 인프라 + 비용 모니터링
```

---

## 핸드오프 컨트랙트

### CPO → CTO

CPO가 PRD에 다음을 확정해야 CTO가 DB/API를 설계한다:
- [ ] 핵심 기능 목록 (MVP에 들어가는 것만)
- [ ] 데이터 흐름 (유저가 뭘 입력하고 뭘 받는지)
- [ ] 비즈니스 모델 (크레딧/구독 → DB 설계에 영향)

인터페이스: `docs/contracts/07_api_data_model.md`

### CPO → CDO

CPO가 유저 플로우를 확정해야 CDO가 화면 설계를 시작한다:
- [ ] 화면 목록 (route 단위)
- [ ] 핵심 인터랙션 (업로드, 편집, 발행)
- [ ] 에디터 편집 단위 (컴포넌트 vs 카드 전체)

인터페이스: `docs/contracts/10_screen_design.md`

### CTO → CDO

CTO가 API 계약을 확정해야 CDO가 데이터 바인딩 컴포넌트를 만든다:
- [ ] 엔드포인트 목록 + 응답 스키마
- [ ] job 상태 모델 (pending/running/done/error)
- [ ] 카드 JSON 구조

인터페이스: `docs/contracts/07_api_data_model.md`

### CDO → CTO (S7 렌더)

CDO가 카드 템플릿 HTML/CSS를 확정해야 CTO가 S7 Playwright 렌더를 연동한다:
- [ ] 템플릿 별 카드 크기 (1080×1080 고정)
- [ ] CSS 변수 네이밍 (--set-* 토큰)
- [ ] 이미지 슬롯 위치 + focal 규칙

인터페이스: `docs/contracts/18_card_design_system.md`

### CTO → CMO

CMO가 실제 파이프라인 출력물(카드뉴스 샘플)을 받아야 마케팅을 시작한다:
- [ ] 샘플 카드뉴스 5편 이상 (도메인 다양)
- [ ] 품질 등급 (CRITICAL 리스크 0인 것만 샘플로)
- [ ] 발행 URL 또는 PNG

인터페이스: `docs/constitution/19_engagement_principles.md`

### CMO → COO

CMO가 채널 전략을 확정해야 COO가 서버/비용 계획을 잡는다:
- [ ] 예상 DAU (서버 사이징에 영향)
- [ ] 발행 주기 (LLM 호출 빈도 → 비용 예측)

---

## 역할 분리: CTO vs CDO (web/ 폴더)

**CTO가 소유**: `backend/`, `web/` — 코드 파일 전체
**CDO가 소유**: `cdo/` — 디자인 스펙, 컴포넌트 명세, UX 결정

실제 Next.js 코드는 CTO가 짠다.
CDO는 `cdo/UI_COMPONENTS.md`에 명세를 작성하고, CTO가 그것을 구현한다.
CDO가 `web/src/` 파일을 직접 수정할 때는 CTO 승인 필요.

---

## 이의 제기 & 역방향 컨트랙트 (Reject 프로세스)

폭포수는 위→아래로만 흐르지 않는다.

**원칙**: 하위 부서가 상위 명세에서 결함을 발견하면 임의 수정 금지.
즉각 상위 부서에 문서를 반려(Reject)하고 재작성 요청.

### 트리거 예시

| 발견 부서 | 상황 | 반려 대상 |
|-----------|------|-----------|
| CTO | CPO 요구 기능이 현재 파이프라인으로 구현 불가 | CPO → PRD.md 재작성 |
| CDO | CTO API 계약에 이미지 슬롯 데이터 누락 | CTO → `docs/contracts/07_api_data_model.md` 수정 |
| CTO | CDO 컴포넌트 명세가 S7 렌더 계약과 충돌 | CDO → UI_COMPONENTS.md 재작성 |
| CMO | 마케팅 카피에 필요한 샘플 카드가 없음 | CTO → 샘플 5편 생성 먼저 |

### 절차

```
1. 결함 발견 부서 → [부서명] 명세 반려: [이유] 형태로 CEO에게 보고
2. CEO가 해당 부서에 재작성 지시
3. 재작성 완료 후 원래 작업 재개
```

직접 수정 절대 금지 — 계약이 꼬이면 아래 부서 전체가 틀린 기반 위에 작업한다.

---

## 문서 위치 원칙

```
docs/              ← 부서간 공유 계약 문서 (원본)
{부서}/            ← 해당 부서의 내부 작업 문서
```

- `docs/` 파일은 복사본 생성 금지. 하나만 존재.
- 부서 내부 문서는 `{부서}/`에만.
- 계약 변경 → docs/ 먼저 수정 → 코드/기획 수정 순서.
