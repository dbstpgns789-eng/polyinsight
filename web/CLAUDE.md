# CLAUDE.md — CTO Web
> PolyInsight Web | Next.js 15 + TypeScript + Tailwind (포트 3000)
> 선행 읽기: 루트 `../CLAUDE.md` → 이 파일

---

## 세션 시작 필독 (읽기 전 답변 시작 금지)

```
../NORTH_STAR.md              ← 북극성·현재 Phase 확인
../PRODUCT.md                 ← 브랜드·유저·안티레퍼런스
../cpo/PRD.md                 ← 유저 플로우·화면 목록
../cpo/ROADMAP.md             ← 현재 단계·포함/제외 기능
../cdo/DESIGN_SYSTEM.md       ← 브랜드 파운데이션·토큰
../cdo/UI_COMPONENTS.md       ← 컴포넌트 명세
../docs/contracts/18_card_design_system.md  ← 카드 스킨/스켈레톤
../docs/contracts/10_screen_design.md   ← 화면 설계
```

---

## 1. 역할 & 범위

Next.js 15 App Router 기반 프로덕션 프론트엔드.
`landing/`(Astro), `frontend/`(React SPA 프로토타입)를 모두 대체한다.

```
src/app/
  page.tsx                  ← 랜딩페이지 (/)
  dashboard/page.tsx        ← 대시보드 (/dashboard)
  editor/[jobId]/page.tsx   ← 카드 에디터 (/editor/:jobId)
```

---

## 2. 화면 구조

```
/dashboard          프로젝트 목록, 통계, 활동 피드
/editor/:jobId      3패널 카드 에디터 (Content | Preview | Design)
upload modal        업로드·처리 오버레이 (별도 route 없음)
export modal        내보내기·다운로드 오버레이 (별도 route 없음)
```

핵심 규칙:
- Upload/Export는 **modal (React Portal)** — 별도 page 금지
- Export preflight는 CRITICAL/unreviewed 항목에 **경고**만, 하드블록 금지 — 최종 판단은 사용자
- 이미지 슬롯은 optional — 이미지 없이 export 허용
- Auto-save 5초 idle

---

## 3. API 연동

백엔드: `http://localhost:8000` (FastAPI)
계약 문서: `../docs/contracts/07_api_data_model.md`

`next.config.ts`의 rewrites로 `/api/*` → `http://localhost:8000/api/*` 프록시.

---

## 4. 포트

```
Next.js dev: 3000
Backend:     8000
```

---

## 5. 커밋 포맷

```
[WEB] brief description
```

---

## 6. CSS 토큰 통합 규칙

> 배경: `frontend/`(파란 hex 토큰)를 `web/`(초록 OKLCH 토큰)으로 이식 시
> 두 시스템이 단절돼 랜딩/에디터 색상 불일치 발생.
> 사례 분석: `docs/constitution/14_migration_retrospective.md`

### @theme에 hex/rgb 직접 쓰지 않는다

```css
/* 금지 */
@theme { --color-brand-600: #2251ee; }

/* 필수 */
@theme { --color-brand-600: var(--accent); }
```

### 이식 전 토큰 매핑 테이블 먼저 작성

| source (이식 대상) | target (web globals.css) |
|-----------------|--------------------------|
| `brand-600` | `var(--accent)` |
| `brand-700` | `var(--accent-hover)` |
| `surface` | `var(--surface)` |
| `surface-subtle` | `var(--bg-subtle)` |
| `surface-border` | `var(--border)` |
| `ink` | `var(--text-1)` |
| `ink-secondary` | `var(--text-2)` |
| `ink-muted` | `var(--text-3)` |

### 이식 완료 기준 = "시각 일치" (빌드 성공이 아님)

이식 후 브라우저에서 두 영역 나란히 열어 색상 눈으로 확인:
- 랜딩 CTA 버튼 색 === 에디터 primary 버튼 색
- 랜딩 배경 색 === 에디터 패널 배경 색

### 이식 순서

```
1. 토큰 매핑 테이블 작성 (선행 필수)
2. 컴포넌트 코드 이전
3. 브라우저 시각 검증 (완료 기준)
```

---

## 7. NEVER (Web 전용)

```
NEVER  @theme 블록에 hex/rgb 색상값 직접 작성
NEVER  "빌드 성공"을 이식 완료 기준으로 삼음
NEVER  Upload/Export를 별도 페이지로 구현
NEVER  Export에 하드블록 구현 — 경고 후 진행만 허용
NEVER  토큰 매핑 테이블 없이 컴포넌트 이식 시작
```

---

## ⚠️ Learned Mistakes
> 실전에서 발생한 치명적 실수. 세션 중 즉시 추가. 절대 삭제 안 함.

| 날짜 | 상황 | 실수 | 규칙 |
|------|------|------|------|
| 2026-05-19 | CSS 이식 | frontend/ hex 토큰을 web/ OKLCH 시스템에 직접 복사 → 브랜드 색 불일치 | 이식 전 매핑 테이블 필수. 완료 기준 = 시각 검증 |
| 2026-06-06 | Export UX | CRITICAL 리스크 항목 CTA 하드블록 구현 → 사용자 판단권 침해, 폐기 | export는 경고 후 진행. 최종 판단은 사용자 |
