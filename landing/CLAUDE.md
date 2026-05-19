# landing/CLAUDE.md
> PolyInsight Landing | Astro 4.16
> 루트의 CLAUDE.md(../CLAUDE.md)를 먼저 읽을 것. 이 파일은 landing 전용 추가 규칙이다.

---

## 1. 이 디렉토리의 역할

랜딩 페이지와 에디터 UI 프로토타입을 담는 Astro 프로젝트.

```
src/pages/index.astro              ← 마케팅 랜딩 페이지
src/pages/editor/[jobId].astro     ← 에디터 UI 목업 (vanilla JS, 실제 API 미연결)
src/components/UploadModal.astro   ← 업로드 모달
src/layouts/Layout.astro           ← 공통 레이아웃 + CSS 변수 정의
```

`editor/[jobId].astro`는 **UI 프로토타입**이다. 실제 카드 에디터 구현체는 `../frontend/`의 React 앱이다.

---

## 2. 공유 콘텐츠 명세 위치

카드 에디터·업로드 모달·내보내기 모달의 콘텐츠 명세는 **`../docs/`가 canonical**이다.

```
../docs/11_upload_modal_content.md
../docs/12_card_editor_content.md
../docs/13_export_modal_content.md
../docs/09_landing_content.md
```

이 `landing/` 디렉토리 안에 11/12/13 복사본을 만들지 않는다.

---

## 3. 개발 서버

```
포트: 4321 (astro.config.mjs에 명시됨)
실행 (루트에서): npm run dev:landing
실행 (landing에서): npx astro dev
```

포트 충돌 없음: backend=8000, frontend=5173, landing=4321

---

## 4. CSS 토큰 시스템

이 프로젝트는 Tailwind를 사용하지 않는다.
모든 색상·간격은 `src/layouts/Layout.astro`의 CSS 변수로 관리된다.

```css
--accent, --accent-hover, --accent-subtle   /* 브랜드 초록 (OKLCH) */
--bg, --bg-subtle, --surface, --border
--text-1, --text-2, --text-3
--dark-bg, --dark-bg-2
--risk-critical, --risk-high, --risk-medium, --risk-ok
```

하드코딩 oklch() 값을 코드에 직접 쓰지 않는다. 반드시 변수 참조.

---

## 5. 브랜드 원칙

상세 내용은 `PRODUCT.md` 참조. 핵심:
- anti-references 목록 스타일 금지
- 워크플로우(3단계 흐름)가 주인공 — 기능 나열 아님
- AI 기술 자랑 없음 — 원문 신뢰성이 핵심 가치

---

## 6. Astro 코드 규칙

- `<style>` 태그는 기본 scoped. 전역 적용 필요 시 `is:global` 사용
- 컴포넌트 frontmatter(`---`) 밖에서 TypeScript 타입 선언 불가
- 이벤트 리스너는 `<script>` 태그 안에서 직접 작성 (MPA 구조)
- 이미지는 `<img>` 직접 사용 (MVP 단순화, Astro `<Image>` 컴포넌트 미사용)

---

## 7. 커밋 포맷

루트 CLAUDE.md의 형식을 따르되 prefix는 `[LANDING]`:
```
[LANDING] brief description
```
