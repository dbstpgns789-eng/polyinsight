# 14 · CSS 이식 실패 회고록

> 2026-05-19 | `frontend/` → `web/` 마이그레이션 과정에서 발생한 설계 실패

---

## 1. 무슨 일이 발생했나

`frontend/` (React SPA, Tailwind v3)와 `landing/` (Astro, OKLCH CSS 변수)를 하나의 `web/` (Next.js, Tailwind v4)으로 통합하는 과정에서, **두 개의 완전히 다른 CSS 토큰 시스템이 하나의 앱 안에서 단절된 채 공존**하게 됐다.

### 실제로 들어온 코드

| 출처 | CSS 방식 | 브랜드 색상 | 예시 |
|------|----------|------------|------|
| `landing/` (Astro) | CSS 변수 직접 참조 | 초록 OKLCH | `color: var(--accent)` |
| `frontend/` (React) | Tailwind 유틸리티 클래스 | 파란 hex | `bg-brand-600` (`#2251ee`) |

### 이식 후 실제 결과

```
랜딩 페이지  → 초록색 CTA, OKLCH 그린 계열
카드 에디터  → 파란색 버튼, hex blue 계열
```

동일 앱 안에서 **랜딩과 에디터가 전혀 다른 브랜드 색상**으로 렌더링된다.  
사용자 입장에서는 완전히 다른 서비스 두 개를 보는 것과 같다.

---

## 2. 왜 발생했나 — 원인 분석

### 원인 1: 이식을 "복사"로 처리했다

`frontend/tailwind.config.js`의 토큰 정의를 `globals.css`의 `@theme` 블록에 그대로 붙여넣었다.

```css
/* 실제로 한 것 — 파란 hex 값 그대로 복사 */
@theme {
  --color-brand-600: #2251ee;   /* frontend 출신, 파란색 */
  --color-surface:   #ffffff;
}
```

해야 했던 것은 **값을 landing의 OKLCH 토큰으로 리매핑**하는 것이었다:

```css
/* 해야 했던 것 — landing 토큰으로 매핑 */
@theme {
  --color-brand-600: var(--accent);        /* oklch(38% 0.14 152) */
  --color-surface:   var(--bg);            /* oklch(98% 0.005 152) */
  --color-ink:       var(--text-1);        /* oklch(16% 0.008 152) */
}
```

### 원인 2: 검증 단계가 없었다

이식 작업의 완료 기준이 "TypeScript 에러 0개 + 빌드 성공"이었다.  
**"실제로 랜딩과 에디터가 같은 브랜드 색상으로 보이는가"**를 눈으로 확인하는 단계가 없었다.

### 원인 3: "이식"과 "통합"을 같은 작업으로 착각했다

- **이식(migration)**: 기존 코드가 새 환경에서 작동하도록 옮기는 것
- **통합(consolidation)**: 두 코드베이스를 하나의 디자인 언어로 통일하는 것

이 작업은 두 작업이 **모두 필요**했지만, 이식만 수행하고 통합을 생략했다.  
이식 단계에서 통합 작업을 선행하지 않으면 기술 부채가 즉시 발생한다.

---

## 3. 올바른 해결 순서

CSS 통합이 포함된 마이그레이션의 올바른 순서:

```
Step 1  토큰 매핑 테이블 작성
        source 시스템의 각 토큰 → target 시스템의 어느 토큰에 해당하는가

Step 2  @theme 블록에 "값 복사" 금지
        반드시 target 토큰의 var() 참조로 작성

Step 3  컴포넌트 이식

Step 4  시각 검증 — 두 시스템이 동일 색상으로 보이는가
        랜딩 버튼과 에디터 버튼이 같은 색인지 눈으로 확인
```

### 이 케이스의 올바른 토큰 매핑 테이블

| frontend 토큰 | landing 대응 | 값 |
|--------------|-------------|-----|
| `brand-600` | `--accent` | `oklch(38% 0.14 152)` |
| `brand-700` | `--accent-hover` | `oklch(32% 0.14 152)` |
| `brand-50` | `--accent-faint` | `oklch(97% 0.018 152)` |
| `surface` | `--surface` / `--bg` | OKLCH |
| `surface-subtle` | `--bg-subtle` | OKLCH |
| `surface-border` | `--border` | OKLCH |
| `ink` | `--text-1` | OKLCH |
| `ink-secondary` | `--text-2` | OKLCH |
| `ink-muted` | `--text-3` | OKLCH |

`risk-*`, `status-*` 계열은 landing에 대응 토큰이 없으므로 새로 정의하되, OKLCH로 작성.

---

## 4. 이 실수가 반복되는 구조적 이유

복수의 CSS 시스템이 관여하는 마이그레이션에서 이 실수가 반복되는 이유:

1. **컴파일러는 색상 의미를 모른다** — `#2251ee`와 `oklch(38% 0.14 152)`가 다른 색임을 TypeScript나 빌드 도구가 잡지 못한다
2. **테스트 커버리지 부재** — 시각적 회귀(visual regression)는 코드 테스트로 잡히지 않는다
3. **"작동하면 됐다"는 압박** — 빌드 성공 = 이식 완료로 단축시키는 관성

---

## 5. 재발 방지 규칙

→ `web/CLAUDE.md` 섹션 6 참조
