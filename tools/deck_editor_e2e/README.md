# 덱 편집기 런타임 하네스 (Phase 3d/3e)

`web/src/components/deck/editorAgent.ts`(iframe 주입 편집 에이전트)의 런타임 회귀 검증.
tsc/eslint가 못 잡는 문자열 주입 ES5 로직을 실제 Chromium에서 구동해 확인한다.
스펙: `docs/superpowers/specs/2026-06-30-deck-direct-manipulation-design.md`,
`docs/superpowers/specs/2026-07-01-deck-multiselect-align-design.md`.

전제: `pip`로 playwright 설치 + `python -m playwright install chromium`.

## deck_harness.py — 코어(서버 불필요)
`AGENT_BODY`를 합성 덱 iframe에 주입, `window.postMessage`로 host 통신, Playwright 합성마우스로 구동.
백엔드/Next 없이 에이전트 로직만 빠르게 검증(31체크).

```
python deck_harness.py            # 전체(baseline·multi·align·undo)
python deck_harness.py multi      # 다중선택/이동만
```

포함: 단일 드래그·리사이즈·undo(3d) / Shift·마퀴 다중선택 / 다중이동(compositeCmd) /
정렬·분배 / 수치 X/Y·W/H / **되돌리기 보편성**(텍스트+레이아웃 혼합 역순 복원, 버튼·Ctrl+Z 동치) / 직렬화 청결.

## fullstack_check.py — Stage 1 (백엔드 저장경로)
uvicorn 기동 상태에서 하네스가 만든 실 편집 HTML을 `PATCH /api/deck/{id}`(X-Render-Token 우회)로
저장 → 재검증·PNG 재렌더 200 확인. 유료 S6 없이 합성 덱 DB 직접삽입.

```
# 루트에서: DB 절대경로 + 렌더토큰으로 uvicorn 기동(env가 .env보다 우선)
DATABASE_URL=<abs>/backend/polyinsight.db RENDER_TOKEN=testtoken \
  python -m uvicorn backend.main:app --port 8000
python tools/deck_editor_e2e/fullstack_check.py
```

## stage2_check.py — Stage 2 (실 브라우저 E2E)
uvicorn + `next dev`(3000) 기동 상태에서 세션 쿠키 주입 → 실 `/deck` 페이지 → 실 DeckEditor iframe에서
편집→다중선택(패널 '다중 N')→정렬→저장 PATCH 200→'저장됨'.

```
TOKEN=$(python tools/deck_editor_e2e/seed_session.py)   # demo@poly.test / demo1234
python tools/deck_editor_e2e/stage2_check.py $TOKEN
```

> 주의: editorAgent 변경 후 `next dev`는 HMR보다 **재시작(fresh)** 이 안정적(turbopack).
> 브라우저 검증은 반드시 `localhost`(Next 16은 `127.0.0.1` dev 리소스 차단).
