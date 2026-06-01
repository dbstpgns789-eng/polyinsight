# web/CLAUDE.md
> PolyInsight Web | Next.js 15 + TypeScript + Tailwind
> 루트의 CLAUDE.md(../CLAUDE.md)를 먼저 읽을 것. 이 파일은 web 전용 추가 규칙이다.

---

## 1. 이 디렉토리의 역할

Next.js 15 App Router 기반 프로덕션 프론트엔드.
`landing/`(Astro)과 `frontend/`(React SPA 프로토타입)를 모두 대체한다.

```
src/app/
  page.tsx                  ← 랜딩페이지 (/)
  dashboard/page.tsx        ← 대시보드 (/dashboard)
  editor/[jobId]/page.tsx   ← 카드 에디터 (/editor/:jobId)
```

---

## 2. 디자인 이식 원칙

`landing/src/layouts/Layout.astro`의 CSS 변수(OKLCH 토큰)를 그대로 이식한다.
`landing/src/pages/`의 HTML 구조와 CSS를 JSX/TSX로 변환하는 것이 주 작업이다.

디자인 토큰 위치: `src/app/globals.css` (:root 변수)

---

## 3. API 연동

백엔드: `http://localhost:8000` (FastAPI)
계약 문서: `../docs/07_api_data_model.md`

`next.config.ts`의 rewrites로 `/api/*` → `http://localhost:8000/api/*` 프록시 설정 예정.

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

## 6. CSS 토큰 통합 규칙 (이식 실패 회고 반영)

> 배경: `frontend/`(파란 hex 토큰)를 `web/`(초록 OKLCH 토큰)으로 이식할 때
> 두 시스템이 단절된 채 공존해 랜딩/에디터 간 브랜드 색상 불일치가 발생했다.
> 자세한 내용: `docs/14_migration_retrospective.md`

### 규칙 1 — @theme 블록에 hex/rgb 값을 직접 쓰지 않는다

외부 컴포넌트를 이식할 때 `@theme` 블록에 색상 값을 복사·붙여넣기 금지.
반드시 `:root`에 정의된 OKLCH 토큰을 `var()`로 참조한다.

```css
/* 금지 */
@theme { --color-brand-600: #2251ee; }

/* 필수 */
@theme { --color-brand-600: var(--accent); }
```

### 규칙 2 — 이식 전에 토큰 매핑 테이블을 먼저 작성한다

컴포넌트 코드 작성 전에, source 토큰 → target 토큰 대응표를 만든다.
대응 토큰이 없으면 `:root`에 OKLCH로 신규 정의하고 `@theme`에서 참조한다.

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

### 규칙 3 — 이식 완료 기준은 "빌드 성공"이 아니라 "시각 일치"다

이식 후 반드시 브라우저에서 두 영역을 나란히 열어 같은 색상인지 눈으로 확인한다.
- 랜딩 CTA 버튼 색 === 에디터 primary 버튼 색
- 랜딩 배경 색 === 에디터 패널 배경 색

TypeScript 통과 + 빌드 성공으로는 색상 불일치를 감지할 수 없다.

### 규칙 4 — 이식과 통합은 별개 작업이다. 순서를 지킨다

```
이식 전: 토큰 매핑 테이블 작성 (선행 필수)
이식:    컴포넌트 코드 이전
이식 후: 시각 검증 (완료 기준)
```

통합(디자인 언어 통일) 없이 이식만 수행하면 기술 부채가 즉시 쌓인다.
