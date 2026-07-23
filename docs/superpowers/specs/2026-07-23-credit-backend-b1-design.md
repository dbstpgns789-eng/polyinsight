# 크레딧 백엔드 (B1) — 설계 스펙

> 2026-07-23 · 브레인스토밍 산출. BM=충전형 크레딧제(B1, 박사님 승인 2026-07-22).
> 선행: `plans.py`(게이트 단일소스)·`db.consume_free_deck`(원자 소비 원형)·docs/07 v2.8(AI디자이너 게이트).
> 범위: 크레딧 잔액 + 원자적 차감/환불 + 게이트 재배선. **Creem 결제·거래내역 UI는 이 스펙 밖.**

## 1. 목적 / 문제

B1 = 기능 차등 폐기. 모든 유저에게 기능은 다 열리고, **작업이 크레딧을 소모**한다.
충전팩은 크레딧 양(+보너스)만 다르다. 고정 단가로 "미터 불안(예측 불가)"을 없앤다.

현재 상태: 게이트가 **binary**(`plan in (pro,lab)`)다 — 유료면 무제한, 무료면 차단.
목표: 유료 세계를 **크레딧 소모**로 바꾼다. 무료체험은 그대로 둔다.

## 2. 두 화폐 공존 (핵심 모델)

| 구분 | 화폐 | 생성 | AI 편집 | export |
|---|---|---|---|---|
| **무료체험**(plan=free) | `free_decks_used` 카운터(기존, 불변) | 평생 1덱, **크레딧 0** | 불가(게이트) | 불가(plan) |
| **유료**(plan=pro, 충전함) | `credits` 잔액 | `DECK_COST` 차감 | `AIEDIT_COST` 차감 | **무과금**(plan 게이트만) |

- 무료 1덱은 크레딧을 쓰지 않는다 — 기존 `free_decks_used` 경로 그대로.
- 충전팩 구매 → `plan='pro'` + `credits += 양`. 이 순간부터 크레딧 세계.
- 퍼널: 무료 1덱 체험 → 막힘 → 충전 → 유료(생성·편집=크레딧, export 열림).
- **면제**: `role='service'`(X-Render-Token)은 `_is_exempt`로, `plan='lab'`(박사님·내부)은 **PAID_PLANS 멤버십**(`plan_of in ("pro","lab")`)으로 면제된다 — 차감 판정 술어가 `plan_of=="pro"` 양성 매칭이라 lab은 자동 배제(차감·게이트 전부 통과). ⚠둘의 출처가 달라 "그냥 _is_exempt 재사용"이 아님(적대검증 지적).
- 크레딧 0인 유료 유저: 생성/편집은 막히지만(402) **export는 됨**(plan 게이트). 재충전하면 다시 생성.

## 3. 스키마

두 컬럼 멱등 추가(기존 plan/free_decks_used 마이그레이션 패턴 복제):

```sql
ALTER TABLE users ADD COLUMN credits INTEGER NOT NULL DEFAULT 0
ALTER TABLE jobs  ADD COLUMN charged_credits INTEGER NOT NULL DEFAULT 0
```

- `users.credits` = 잔액. **잔액만(balance-only)**, 거래내역(ledger) 테이블 없음 — 사용내역 UI(P1-2) 착수 시 추가. 기존 `free_decks_used`도 잔액만이라 일관. YAGNI.
- `jobs.charged_credits` = **이 잡 생성에 선차감된 크레딧(환불 근거)**. 적대검증 blocker(§13-①) 대응 — 환불을 휘발성 인자가 아니라 **DB 행**에 남겨야 재시작 후에도 복구 가능. 무료 소비/면제 잡은 0.
- 기존 유저 백필: `credits=0`(면제 lab은 크레딧 무관, DEFAULT 0으로 족함). 기존 잡 백필: `charged_credits=0`.
- `CREATE TABLE users`·`CREATE TABLE jobs`(신규 DB)에도 각 컬럼 추가(환경별 스키마 표류 방지).

## 4. 차감 단가 (상수)

`plans.py`에 상수로 둔다. **값은 자리표시자 — 나중 튜닝 가능**(Mirra 실측 단가 참고: 전체수정5·캡션3·이미지3·장표5cr).

```python
DECK_COST = 10       # 덱 1건 생성
AIEDIT_COST = 2      # 자연어 편집 1회(nlpatch·propose)
# export = 0 (무과금)
```

고정 단가 = 예측 가능. 유저는 "덱 하나 10, 편집 2"를 미리 안다(작업량 미터기 불안 해소).

## 5. DB 함수 (`db.py`, `consume_free_deck` 복제)

```python
async def consume_credits(user_id: int, cost: int) -> bool:
    """원자적 차감(잡 없는 동기 작업용 = AI 편집). 성공=True. 부족/cost≤0=False.
    UPDATE 한 문장이 잔액 검사까지 하므로 check-then-act 레이스 없음."""
    if cost <= 0: return False
    UPDATE users SET credits = credits - :cost WHERE id = :id AND credits >= :cost
    # return rowcount > 0

async def consume_credits_for_job(user_id: int, job_id: str, cost: int) -> bool:
    """덱 생성용 — 차감 + 잡에 환불근거 각인을 **한 트랜잭션**으로. §13-①·③ 대응.
    차감만 되고 각인이 안 되는 창(재시작 시 환불 못함)을 원천 차단."""
    if cost <= 0: return False
    BEGIN
    UPDATE users SET credits = credits - :cost WHERE id = :id AND credits >= :cost
    if rowcount == 0: ROLLBACK; return False
    UPDATE jobs SET charged_credits = :cost WHERE id = :job_id
    COMMIT; return True

async def refund_job_credits(job_id: str) -> None:
    """잡의 선차감 크레딧을 **멱등** 환불. _log_done(ERROR)·recover_stale_jobs 둘 다 호출.
    각인을 0으로 지우는 게 이중환불 방어(WHERE charged_credits>0)."""
    BEGIN
    # 잡 소유자 잔액에 환불 + 각인 소거를 원자로. charged_credits>0일 때만(멱등).
    UPDATE users SET credits = credits +
        (SELECT charged_credits FROM jobs WHERE id = :job_id AND charged_credits > 0)
        WHERE id = (SELECT user_id FROM jobs WHERE id = :job_id AND charged_credits > 0)
    UPDATE jobs SET charged_credits = 0 WHERE id = :job_id
    COMMIT
    # 구현 시 정확한 SQL은 TDD로. 불변식: charged_credits>0인 잡만 1회 환불, 이후 0.

async def add_credits(user_id: int, amount: int) -> None:
    """충전. plan='pro' 승격 + 잔액 가산(한 트랜잭션). amount<=0이면 무효(no-op)."""
    if amount <= 0: return
    UPDATE users SET credits = credits + :amount, plan = 'pro'
    WHERE id = :id AND plan NOT IN ('lab')   # lab(면제) 강등 금지

async def get_credits(user_id: int) -> int   # 행 없으면 0
```

- 덱 생성 = `consume_credits_for_job`(차감+각인 원자). AI 편집 = `consume_credits`(잡 없음, 성공 후 차감이라 환불 불필요 — §7).
- 환불은 오직 `refund_job_credits`(멱등). 별도 `refund_credits`는 두지 않는다 — AI 편집은 성공에만 과금해 환불 경로 자체가 없다.
- `add_credits`: `amount<=0` no-op(음수 충전 방어). `plan='lab'`은 승격 안 함(면제 유지).

## 6. 게이트 재배선 (`plans.py`)

**두 층으로 명확히 분리** — 어느 규제든 같은 모양:
- **1층(접근 게이트)**: 이 기능을 쓸 자격이 있나? free/paid 판정. 파일 읽기 전 조기 거부.
- **2층(잔액 원자 소비)**: `consume_credits`가 레이스까지 막는 진짜 강제. 부족하면 `ERR-CREDIT-LOW`.

```python
def author_charges_credits(user) -> bool:   # 유료(pro)이고 면제 아님 → 생성이 크레딧 차감
    return not _is_exempt(user) and plan_of(user) == "pro"

def require_can_author(user) -> None:
    # 면제/lab → 통과. free → 무료 카운터 소진이면 ERR-PLAN-AUTHOR.
    # pro → 잔액 < DECK_COST 면 ERR-CREDIT-LOW (조기 거부, 50MB 읽기 전).
    ...

def require_can_ai_designer(user) -> None:
    # free/미면제 → ERR-PLAN-AI-DESIGNER(기존, 접근 자체 차단).
    # pro → 잔액 < AIEDIT_COST 면 ERR-CREDIT-LOW.

def can_export(user) -> bool:        # 변화 없음 (plan in PAID_PLANS)
```

- 접근 게이트는 **에러를 regime별로 다르게** 낸다: free 소진 → `ERR-PLAN-AUTHOR`(업그레이드 유도) / paid 잔액부족 → `ERR-CREDIT-LOW`(충전 유도). 프론트가 두 CTA를 분기.
- 조기 잔액 체크(1층)와 원자 소비(2층)는 **belt-and-suspenders** — 기존 free 경로도 `require_can_author`(조기) + `consume_free_deck`(원자) 이중이라 일관.

**신규 에러**: `ERR-CREDIT-LOW`(402, gate_kind="credits") — 잔액 부족.
메시지: "크레딧이 부족해요. 충전하면 계속 만들 수 있어요." (유저 말 — 'credit balance' 같은 내부어 금지, test_credit_error 교훈.)

## 7. 라우터 훅 재배선

### `POST /deck/upload` (deck.py:69-100)
잡을 **먼저 만들고**(각인 대상 필요), 그 다음 차감+각인을 원자로. free는 기존 순서 유지.
```
require_can_author(user)                        # 무료 소진 or 유료 잔액부족 → 402(조기, 읽기 전)
...
if should_consume_free_deck(user):              # free 플랜 (기존, 변화 없음)
    if not consume_free_deck(...): raise author_gate_error   # job 생성 전
job_id = uuid; create_job(...)
if author_charges_credits(user):                # 유료(pro)
    if not consume_credits_for_job(user_id, job_id, DECK_COST):
        delete_job(job_id); raise credit_low_error          # 레이스 패자·잔액부족
try:
    background_tasks.add_task(run_authoring_pipeline, job_id, ...)
except Exception:
    refund_job_credits(job_id)                  # §13-③ 스케줄 실패 창 봉합
    raise
```
- 무료: job 생성 전 선차감(기존 레이스 방어). 유료: job 생성 후 **차감+각인 원자**(각인이 재시작 환불의 근거). 둘 **상호배타**.
- `run_authoring_pipeline`에 **크레딧 인자를 넘기지 않는다** — 환불 근거는 `jobs.charged_credits`(DB)다.

### 실패 환불 — **두 진입점 모두** `refund_job_credits(job_id)` (멱등)
1. `pipeline._log_done(status==ERROR)` — 정상 실행 중 실패(기존 `refund_free_deck` 옆에 추가).
2. `db.recover_stale_jobs` — **재시작으로 소실된 잡을 ERROR로 뒤집을 때 반드시 환불**(§13-① blocker). 각 stale 잡에 `refund_job_credits` 호출.
- 멱등(`WHERE charged_credits>0` + 각인 소거)이라 두 경로가 겹쳐도 **1회만** 환불. 이게 blocker의 핵심 봉합.
- 무료 카운터 환불(`refund_free_deck`)은 기존 그대로($0, 재시작 바이패스 방치 유지 — 실화폐 아님).

### `POST /deck/{id}/nlpatch`·`/nlpatch/propose` (deck.py:159, 196) — **검증 통과 후 차감**
```
require_can_ai_designer(user)                   # free→402(게이트), pro→잔액 조기검사
new_html = await apply_nl_patch(...)            # LLM 호출
if "data-screen-label" not in new_html: raise 422   # ★차감 전 — no-op이면 과금 0
if author_charges_credits(user):                # 유료(pro)
    if not consume_credits(user_id, AIEDIT_COST): raise credit_low_error
# 저장/렌더 → 응답
```
- **성공(계약 통과)에만 차감** — §13-② 대응(422 구조거부·LLM 예외 모두 차감 전이라 no-op 과금 없음, 환불 경로 불필요).
- 조기 잔액검사(require_can_ai_designer)로 못 낼 유저는 LLM 호출조차 안 함(원가 방어). 검사~차감 사이 레이스로 잔액이 빠지면 원자 소비가 402(드묾, LLM 원가만 흡수).
- propose(미저장 프리뷰)도 동일 — LLM 실호출이라 성공 시 과금이 옳음(charge-per-LLM-call). PATCH 직접편집·reverify·caption은 **무 LLM = 무과금**(각각 기존 무게이트 유지, plans.py 도킹스트링에 명문).

### export (변화 없음)
`require_can_export`만(deck.py:363, export.py:28/64, jobs.py:115). 크레딧 미차감.

### 부분 렌더 과금 정책 (§13-④)
`pipeline.py`는 `status = DONE if images else ERROR` — 1장이라도 렌더되면 DONE. **정책: 1장 이상 = 전달된 산출물 = 전액 과금(환불 없음)**, 0장 = ERROR = 전액 환불(위 두 훅). 부분 덱도 유저가 편집·재생성 가능한 자산이라 전액 과금이 기본. (비례 환불은 ledger 필요 → P1-2 이후 재검토.)

## 8. API 표면

잔액은 **기존 `GET /api/auth/me` 응답에 `credits` 필드로** 노출한다(프론트가 이미 유저 상태를 여기서 읽음 — DRY). 전용 `/me/credits` 폴링 엔드포인트는 만들지 않는다(YAGNI — 소비자=P1-2 위젯이 생기고 갱신 패턴이 확정될 때 추가).
```
GET /api/auth/me → { ..., "plan": str, "credits": int, "canAuthor": bool, "canExport": bool, ... }
```
- **충전 엔드포인트는 이 스펙 밖**(Creem 웹훅 붙일 때). 지금은 `add_credits` 함수 + 관리자/테스트 수동 충전으로 충분.

## 9. 에러 처리

- `ERR-CREDIT-LOW`(402): 유료 유저 잔액 부족. 프론트 → "충전" CTA.
- `ERR-PLAN-AUTHOR`(402, 기존): 무료 1덱 소진. 프론트 → "업그레이드/충전" CTA.
- `consume_credits` 실패는 예외 아님(False 반환) → 호출부가 402로 변환(레이스 방어 일관).
- 음수/0 cost 방어(악용 차단).

## 10. 테스트 (TDD, `backend/tests/`)

신규 `test_credits.py`:
- `consume_credits`: 잔액충분→차감·True / 부족→불변·False / cost≤0→False / **동시 2건**(원자성, 하나만 성공).
- `consume_credits_for_job`: 성공 시 차감+`jobs.charged_credits` 각인 **동시** / 부족 시 **둘 다 불변**(롤백, 각인 0).
- `refund_job_credits`: 환불+각인 소거 / **2회 호출해도 1회만 환불**(멱등, §13-①·③ 핵심).
- `add_credits`: 가산+plan승격 / `amount<=0` no-op / lab은 승격 안 됨.
- 게이트: 무료 1덱 후 생성 차단(ERR-PLAN-AUTHOR) / 유료 생성 시 DECK_COST 차감 / 잔액부족 402(ERR-CREDIT-LOW) / **export 무과금**(크레딧 불변) / lab·service 면제(차감 0).
- **§13-② AI편집 422**: 구조 깨진 결과로 422 거부 시 크레딧 **불변**(차감 전 거부).
- **§13-① 재시작 환불**: `charged_credits>0`인 stale 잡을 `recover_stale_jobs`가 ERROR로 돌릴 때 크레딧 복구.
- **§13-④ 부분 렌더**: images≥1 → DONE → 전액 과금(환불 0) / images=0 → ERROR → 전액 환불.

기존 `test_free_trial.py` 회귀: 무료 경로 불변 확인.

## 11. 범위 밖 (명시)

- **Creem 결제/웹훅** — 충전은 `add_credits` 함수까지. 실결제는 Creem 키(세훈) 후 별도.
- **거래내역(ledger) 테이블·사용내역 UI** — P1-2.
- **잔액 위젯·소모량 뱃지 프론트** — P1-2(이 스펙은 `GET /me/credits`까지).
- **발행(publish) 크레딧** — Phase 2(Meta 심사).
- 단가 최종값 캘리브레이션 — 상수만 두고 나중 조정.

## 12. docs/ 반영 (구현 시)

헌법 "docs 먼저": 구현 착수 시 `docs/contracts/07_api_data_model.md`에 크레딧 스키마·차감 규칙·`GET /me/credits`·`ERR-CREDIT-LOW` 반영(v2.9). 이 브레인스토밍 스펙과 계약 문서는 별개 — 계약 문서가 정본.

## 13. 적대검증 로그 (2026-07-23)

5개 렌즈 25 에이전트 병렬 공격 → 코드 대조 검증. **6 confirmed / 14 rejected**. 구별되는 결함 4개, 위 §3·§5·§7·§10에 반영:

| # | 심각도 | 결함 | 봉합 |
|---|---|---|---|
| ① | **blocker** | 재시작/재배포로 소실된 잡을 `recover_stale_jobs`가 ERROR 마킹만 하고 환불 안 함 → 선차감 크레딧 영구 증발(휘발성 인자로는 복구 불가, ledger 없어 추적도 불가). 매일 18:00 재배포가 진행 잡 몰살하는 운영 상수라 실발생. | 환불근거를 `jobs.charged_credits`(DB)에 각인. `_log_done`·`recover_stale_jobs` 두 진입점 모두 `refund_job_credits`(멱등) 호출. |
| ② | major | AI편집(nlpatch/propose): LLM 성공 후 결과 구조가 깨져 422 거부되는데 차감은 이미 됨 → 변화 0에 과금(모델 드리프트로 상습). 3개 렌즈 독립 발견. | **검증(data-screen-label) 통과 후 차감.** 422·LLM예외 모두 차감 전이라 no-op 과금 원천 차단. |
| ③ | minor | `consume` 성공 후 `create_job`/`add_task` 실패 창 → 환불 훅 안 돎. | ①의 DB 각인이 커버(recover 스윕) + `add_task` 실패 시 즉시 `refund_job_credits`. |
| ④ | minor | 부분 렌더(7장 중 3장) → `status=DONE` → 전액 과금·환불 미정의. | **정책 명문화**: 1장 이상=전달 산출물=전액 과금 / 0장=ERROR=전액 환불. (비례 환불은 ledger 필요→P1-2.) |

기각된 14건 요지: 대부분 "아직 미구현 코드에 대한 가정", "범위 밖 Creem 웹훅 멱등성", "lab 면제가 실제 슈도코드(`plan=='pro'` 양성판정)에선 안전"으로 반박됨. 단 §2 "면제=_is_exempt 재사용" 문구가 부정확(lab 면제 실체는 PAID_PLANS 멤버십)하다는 지적은 타당 — 표현만 흠, 동작은 안전.
