# backend/templates/CLAUDE.md
> Jinja2 카드 템플릿 = **시각 계약(canonical visual contract)**.
> React 캔버스(웹 에디터)는 이 템플릿의 출력을 미러링한다.

---

## 1. 이 디렉토리의 역할

이 디렉토리의 12개 `*.html` 파일은 PolyInsight 카드뉴스의 **시각적 정답지**다.

- **S7 PNG export 파이프라인**이 이 템플릿을 직접 Jinja2로 렌더링하여 Playwright로 PNG 스크린샷
- **웹 에디터(`web/src/components/cards/templates/*Card.tsx`)**는 이 템플릿과 픽셀 단위로 일치하도록 작성됨

즉, 동일한 카드뉴스의 모습이 **두 곳에서 정의**되어 있다:
1. `backend/templates/{name}.html` — 백엔드 PNG export용 (정답지)
2. `web/src/components/cards/templates/{Name}Card.tsx` — 웹 에디터 미러

---

## 2. NEVER

```
NEVER  Jinja 템플릿만 수정하고 React 컴포넌트는 그대로 둔다
NEVER  React 컴포넌트만 수정하고 Jinja 템플릿은 그대로 둔다
NEVER  CI 시각 회귀 실패를 우회하거나 무시한다
NEVER  새로운 카드 템플릿을 한쪽에만 추가한다
```

---

## 3. 수정 절차

카드 디자인을 바꾸려면:

1. **백엔드 템플릿 먼저 수정** — `{name}.html` 갱신
2. **React 컴포넌트 동기 수정** — `web/src/components/cards/templates/{Name}Card.tsx` 갱신
3. **시각 회귀 테스트 통과 확인** — Jinja PNG 출력과 React 캔버스 스크린샷이 픽셀 차이 0.5% 이하인지
4. **두 변경을 같은 PR에 묶어 머지** — 분리 머지 금지

새 카드 템플릿 추가 시:

1. `backend/templates/{name}.html` 작성
2. `backend/agents/s7_renderer.py` `LAYOUT_TEMPLATES`, `IMAGE_SLOT_TYPES` 등록
3. `web/src/components/cards/templates/{Name}Card.tsx` 작성
4. `web/src/components/cards/index.ts` `CARD_COMPONENTS` 등록
5. `web/src/lib/templateFields.ts` `TEMPLATE_FIELDS` 스키마 등록
6. 시각 회귀 fixture 추가

---

## 4. 디자인 토큰 동기화

CSS 변수와 디자인 토큰은 두 곳에서 정의:

| 백엔드 (정답지) | 웹 (미러) |
|---|---|
| `backend/templates/_shared.css` | `web/src/components/cards/cards.module.css` |

값이 달라지면 시각 회귀가 실패한다. `_shared.css`를 수정하면 `cards.module.css`도 정확히 동일하게 갱신.

---

## 5. 왜 이렇게 두 곳에서 정의되어 있는가

`docs/superpowers/specs/2026-06-01-editor-screen-definition.md` 참조.

- 빅뱅 마이그레이션 (iframe → React 캔버스) 시점에 S7 export 파이프라인을 건드리지 않는 것을 선택
- Jinja 템플릿이 시각 정답지로 유지되고, React가 미러
- 운영 단순성을 위해 Next.js URL 스크린샷 방식을 거부 (S7은 백엔드 단독으로 동작 가능)
- 대신 시각 회귀 테스트가 drift를 차단
