# 진행 렌더 리빌 (RENDER 조기 입장) Implementation Plan

> **For agentic workers:** subagent-driven. 체크박스 추적.

**Goal:** 덱 생성의 마지막 RENDER 단계에서 사용자를 뷰로 **조기 입장**시키고, 카드 PNG가 렌더되는 대로 **한 장씩 나타나게**(스켈레톤 셔머 → 실제 카드, "N/M 그리는 중") 해 대기를 리빌 모먼트로 바꾼다.

**Architecture:** 파이프라인은 이미 렌더 전에 `save_authored_deck`(html·검증) + `stage=RENDER`를 세팅한다 → **백엔드는 `render_deck`가 카드를 캡처하는 즉시 DB에 저장**(현재는 전부 렌더 후 일괄)만 추가하면 됨. `db._connect()`는 호출마다 새 aiosqlite 연결(공유·루프고정 없음, busy_timeout=5000)이라 격리된 렌더 스레드에서 저장해도 안전. **프론트는 폴링이 `stage==='RENDER'`면 조기 입장**(getDeck html 이미 준비) + DeckViewer가 카드별 재시도 폴링·스켈레톤·리빌.

**Tech Stack:** FastAPI·Playwright(백)/Next React(프론트). 테스트=실제 render_deck 호출(Playwright=무료)+라이브 E2E.

> **불변:** 저작 HTML·검증·카드 픽셀 결과 동일해야 함(리빌은 타이밍만 바꿈, 내용 X). 실패(0카드)→ERROR 경로 유지.

---

## Task 1: render_deck 카드별 즉시 저장 (백엔드)

**Files:** Modify `backend/agents/deck/deck_renderer.py`, `backend/agents/deck/pipeline.py`

- [ ] **Step 1: `deck_renderer.py` — 캡처 즉시 저장**
  `_render_async` 시그니처에 `job_id` 추가. 캡처 루프(현 116-124)를 교체:
```python
async def _render_async(html: str, scale: int, timeout_s: float, job_id: str | None = None) -> tuple[list[bytes], list[str]]:
```
  루프:
```python
            for i in range(count):
                try:
                    png = await asyncio.wait_for(
                        loc.nth(i).screenshot(type="png"), timeout=timeout_s
                    )
                    images.append(png)
                    logger.info("deck render: card %d (%d bytes)", i + 1, len(png))
                    if job_id:
                        try:
                            await db.save_card_image(job_id, i + 1, png)   # 캡처 즉시 저장 → 프론트가 한 장씩 봄
                        except Exception as exc:
                            warnings.append(f"deck render: card {i + 1} save error — {exc}")
                except Exception as exc:
                    warnings.append(f"deck render: card {i + 1} error — {exc}")
```
  `_render_sync`도 `job_id` 인자 추가 + `_render_async(html, scale, timeout_s, job_id)`로 전달. `render_deck`(현 146-153)에서 `run_in_executor(_deck_pool, _render_sync, html, scale, timeout_s, job_id)`로 job_id 전달.

- [ ] **Step 2: `pipeline.py` — 중복 저장 루프 제거(렌더가 이미 저장)**
  `_execute`의 렌더 후 저장 루프(현 181-185, `for i, png in enumerate(images, start=1): save_card_image`)를 제거. 렌더가 진행 중 저장했으므로 중복. 대신 카운트·정리만:
```python
    images, render_warns = await render_deck(html, job_id=job_id)
    warnings.extend(render_warns)
    if not images:
        warnings.append("deck render: 0 cards rendered")
    else:
        await db.delete_card_images_above(job_id, len(images))
```
  (DONE/ERROR 판정 `status = JobStatus.DONE if images else JobStatus.ERROR`는 유지.)
  **또한** `persist_edited_deck`(편집 저장 경로, 현 63-73의 save 루프)도 동일하게 정리 — render_deck가 저장하므로 그 함수의 `for i, png in enumerate(images, start=1): save_card_image` 루프 제거, `if not images` 경고 + `delete_card_images_above`만 유지.

- [ ] **Step 3: 실제 렌더 검증(무료 — Playwright, LLM 없음)**
  기존 덱 html로 render_deck를 직접 호출해 카드가 **진행 중 저장**되는지 확인하는 임시 스크립트:
```python
# scratch_render_test.py (임시)
import asyncio, sqlite3
from backend.agents.deck import db_reset  # placeholder — 아래처럼 직접
from backend.core import db
from backend.agents.deck.deck_renderer import render_deck

async def main():
    con = sqlite3.connect('polyinsight.db')
    html = con.execute("SELECT html FROM authored_deck LIMIT 1").fetchone()[0]
    con.close()
    jid = 'render-test-tmp'
    await db.create_job(jid, 'render test', user_id=1)
    imgs, warns = await render_deck(html, job_id=jid)
    print('rendered', len(imgs), 'cards; warnings', warns)
    saved = await db.get_card_images(jid)
    print('saved in DB during render:', sorted(saved.keys()))
    # cleanup
    con = sqlite3.connect('polyinsight.db')
    for t in ['card_images','jobs']: con.execute(f"DELETE FROM {t} WHERE job_id=?", (jid,))
    con.commit(); con.close()

asyncio.run(main())
```
  실행: `cd repo && PYTHONUTF8=1 .venv/Scripts/python.exe scratch_render_test.py`
  기대: `rendered 7 cards` + `saved in DB during render: [1,2,3,4,5,6,7]`(저장이 render_deck 안에서 일어남 증명). 확인 후 스크립트 삭제.

- [ ] **Step 4: 백엔드 회귀** — `.venv/Scripts/python.exe -m pytest backend/tests/ -q` (기존 nlpatch/patch/deck 테스트가 render_deck를 mock하므로 그린 유지 확인; mock이 save를 안 하는 경우 카드수 로직 확인).

- [ ] **Step 5: 커밋**
```bash
git add backend/agents/deck/deck_renderer.py backend/agents/deck/pipeline.py
git commit -m "[BE] 렌더 카드별 즉시 저장 — 진행 리빌 기반(일괄 저장 폐기) (RENDER 조기입장)"
```

---

## Task 2: 조기 입장 + 진행 리빌 (프론트)

**Files:** Modify `web/src/app/deck/[jobId]/page.tsx`, `web/src/components/deck/DeckViewer.tsx`, `web/src/app/globals.css`

- [ ] **Step 1: `page.tsx` 폴링 — RENDER 단계 조기 입장**
  `rendering` 상태 + `deckLoadedRef` 추가:
```typescript
  const [rendering, setRendering] = useState(false)
  const deckLoadedRef = useRef(false)
```
  폴링 effect의 상태 분기(현 147-151)를 교체:
```typescript
        if (r.data.status === 'DONE' || r.data.status === 'ERROR') {
          const d = await getDeck(jobId)
          if (!cancelled) { setDeck(d.data as DeckPayload); setRendering(false) }
          return
        }
        // 콘텐츠 준비됨(RENDER 단계) → 조기 입장(카드는 렌더되는 대로 채워짐)
        if (r.data.stage === 'RENDER' && !deckLoadedRef.current) {
          try {
            const d = await getDeck(jobId)
            if ((d.data as DeckPayload)?.html && !cancelled) {
              setDeck(d.data as DeckPayload); setRendering(true); deckLoadedRef.current = true
            }
          } catch { /* 아직 → 다음 폴링 */ }
        }
```
  (RENDER 중에도 계속 폴링하도록 이 분기는 `return` 없이 아래 `timer = setTimeout(poll, 1500)`로 흐른다.)
  DeckViewer에 `rendering` 전달:
```tsx
            <DeckViewer jobId={jobId} cardCount={deck.cardCount || 7} ver={ver} rendering={rendering} onEditCard={enterEditAt} />
```
  뷰 진입 조건: 현재 `status !== DONE && !== ERROR`면 GenerationTheater를 반환(현 254-256). 이걸 **조기 입장 시 뷰를 그리도록** 변경 — `deck?.html`이 있으면(=RENDER 조기 입장 or DONE) 뷰/편집 렌더로 진행, 없으면 Theater:
```typescript
  // 진행 중이라도 콘텐츠(html)가 준비되면(RENDER 조기입장) 뷰로. 아니면 진행화면.
  if ((status !== 'DONE' && status !== 'ERROR') && !deck?.html) {
    return <GenerationTheater stage={stage || 'S1'} progress={progress} />
  }
```

- [ ] **Step 2: `DeckViewer.tsx` — 스켈레톤 셔머 + 카드별 재시도 + N/M + 리빌**
  `rendering?: boolean` prop 추가. 렌더 중이면 `tick`을 1.5s마다 증가시켜 미완 카드 img를 재시도(캐시버스트). `CardImg`는 로드 성공 시 `onReady()` 콜백으로 부모가 로드 수 집계. 미완이면 셔머 스켈레톤.
```tsx
interface Props { jobId: string; cardCount: number; ver: number; rendering?: boolean; onEditCard: (index: number) => void }

// ... 컴포넌트 내부:
  const [tick, setTick] = useState(0)
  const [ready, setReady] = useState<Set<number>>(new Set())
  useEffect(() => {
    if (!rendering) return
    const t = setInterval(() => setTick((x) => x + 1), 1500)   // 미완 카드 재시도
    return () => clearInterval(t)
  }, [rendering])
  const markReady = (num: number) => setReady((s) => (s.has(num) ? s : new Set(s).add(num)))
```
  렌더 중 표시(스트립 위):
```tsx
      {rendering && ready.size < n && (
        <div className="flex items-center gap-2 text-[12px] text-ink-3">
          <span className="w-3.5 h-3.5 rounded-full border-2 border-forest-green border-t-transparent animate-spin" aria-hidden="true" />
          카드 그리는 중 {ready.size} / {n}
        </div>
      )}
```
  `CardImg`: `rendering`·`tick`·`onReady` 반영. 미완(에러/미로드)면 셔머 스켈레톤(`pi-shimmer`), 로드되면 fade-in.
```tsx
function CardImg({ jobId, num, ver, thumb, rendering, tick, onReady }: {
  jobId: string; num: number; ver: number; thumb?: boolean; rendering?: boolean; tick?: number; onReady?: (n: number) => void
}) {
  const [loaded, setLoaded] = useState(false)
  const bust = rendering ? `${ver}-${tick}` : (ver || undefined)   // 렌더 중엔 tick으로 재시도
  return (
    <div className="w-full h-full rounded-[inherit] overflow-hidden relative">
      {!loaded && <div className="absolute inset-0 pi-shimmer" aria-hidden="true" />}
      <img key={bust} src={getDeckCardUrl(jobId, num, bust)} alt={`카드 ${num}`}
        className={`w-full h-full object-cover rounded-[inherit] transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
        style={thumb ? undefined : { boxShadow: loaded ? 'var(--shadow-modal)' : 'none' }}
        onLoad={() => { setLoaded(true); onReady?.(num) }}
        onError={() => setLoaded(false)} />
    </div>
  )
}
```
  큰 카드·썸네일의 `CardImg` 호출부에 `rendering={rendering} tick={tick} onReady={markReady}` 전달. (미완 카드 클릭→편집은 렌더 중엔 비활성 권장: "이 카드 편집" 버튼을 `rendering && !ready.has(idx+1)`이면 숨김.)

- [ ] **Step 3: `globals.css` — 셔머 키프레임** (`@layer base` 밖, 최상위. 주석에 `*/` 문자열 금지)
```css
@keyframes pi-shimmer-move { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
.pi-shimmer {
  background: linear-gradient(100deg, var(--bg-subtle) 40%, var(--surface) 50%, var(--bg-subtle) 60%);
  background-size: 200% 100%;
  animation: pi-shimmer-move 1.4s ease-in-out infinite;
}
```

- [ ] **Step 4: 검증** — `cd web && npx tsc --noEmit`(clean) · `npx vitest run`(전부) · `npm run lint`(신규 에러 없음).

- [ ] **Step 5: 커밋**
```bash
git add web/src/app/deck/[jobId]/page.tsx web/src/components/deck/DeckViewer.tsx web/src/app/globals.css
git commit -m "[WEB] RENDER 조기 입장 + 진행 리빌 — 스켈레톤 셔머·카드별 재시도·N/M (RENDER 조기입장)"
```

---

## Task 3: 라이브 E2E

**Files:** (없음)

RENDER 조기 입장은 실제 파이프라인 실행 중에만 자연 발생 → 유료 LLM(AUTHOR) 필요. **비용 회피**: 시드 잡을 `stage=RENDER` 상태로 두고 백그라운드로 render_deck를 느리게 돌려 프론트가 카드가 하나씩 채워지는 걸 보이게 시뮬레이트.

- [ ] **Step 1: 프론트 재컴파일**(`.next` 필요 시 삭제). 백엔드 재기동(deck_renderer 변경 반영).
- [ ] **Step 2: 시뮬레이션 E2E** — 테스트 유저 signup + 잡 시드(`stage=RENDER`, `status=RUNNING`, authored_deck html 있음, card_images 비움). 브라우저 `/deck/<jid>` 진입 → **GenerationTheater 아닌 뷰로 조기 입장** + "카드 그리는 중 0/7" + 스켈레톤 셔머 확인. 그 상태에서 백엔드로 render_deck를 돌려 card_images를 채우고 status=DONE으로 → 프론트가 카드를 하나씩 채우고 인디케이터가 사라지는지 스크린샷 확인. 시드·유저 정리.
- [ ] **Step 3: 회귀** — 백엔드 pytest·vitest·tsc 그린. **스크린샷으로 시각 확인**(UI/UX 게이트): 셔머·리빌·완료 상태.
- [ ] **Step 4: 보고**(스크린샷 첨부).

---

## Self-Review
| 요구 | 태스크 |
|---|---|
| RENDER 단계 조기 입장 | 2(폴링 stage===RENDER) |
| 카드 한 장씩 실제 리빌 | 1(per-card 저장)·2(재시도·onLoad) |
| 스켈레톤 셔머 (지루함 해소) | 2·3 |
| N/M 진행 표시 | 2 |
| 실패(0카드)→ERROR 유지 | 1(status 판정 보존) |
| 모트 픽셀 불변 | 1(타이밍만 변경, 캡처 동일) |

**주의:** 백엔드는 모트 파이프라인 → Task 1 Step 3 실제 렌더 검증 필수(무료). Task 3 시각 검증 필수(UI/UX 게이트).
