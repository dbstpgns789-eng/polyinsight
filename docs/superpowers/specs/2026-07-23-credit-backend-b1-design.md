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
- **면제**: `role='service'`(X-Render-Token)·`plan='lab'`(박사님·내부)은 게이트/차감 전부 면제(기존 `_is_exempt` 재사용).
- 크레딧 0인 유료 유저: 생성/편집은 막히지만(402) **export는 됨**(plan 게이트). 재충전하면 다시 생성.

## 3. 스키마

`users`에 컬럼 하나 멱등 추가(기존 plan/free_decks_used 마이그레이션 패턴 복제):

```sql
ALTER TABLE users ADD COLUMN credits INTEGER NOT NULL DEFAULT 0
```

- **잔액만(balance-only).** 거래내역(ledger) 테이블은 만들지 않는다 — 사용내역 UI(P1-2) 착수 시 추가.
  근거: 기존 `free_decks_used`도 잔액만이라 일관. YAGNI.
- 기존 유저 백필: `credits=0`. (면제 lab 유저는 크레딧과 무관하므로 백필 불필요, DEFAULT 0으로 족함.)
- `CREATE TABLE users`(신규 DB)에도 `credits INTEGER NOT NULL DEFAULT 0` 추가.

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
    """원자적 차감. 성공=True. 잔액 부족/음수 cost면 아무 것도 안 바꾸고 False.
    UPDATE 한 문장이 잔액 검사까지 하므로 check-then-act 레이스 없음."""
    UPDATE users SET credits = credits - :cost
    WHERE id = :id AND credits >= :cost
    # return rowcount > 0

async def refund_credits(user_id: int, cost: int) -> None:
    """파이프라인 실패 시 선차감 환불(가산). free_deck 환불과 같은 훅."""
    UPDATE users SET credits = credits + :cost WHERE id = :id

async def add_credits(user_id: int, amount: int) -> None:
    """충전. plan='pro'로 승격 + 잔액 가산(한 트랜잭션)."""
    UPDATE users SET credits = credits + :amount, plan = 'pro'
    WHERE id = :id AND plan NOT IN ('lab')   # lab(면제) 강등 금지

async def get_credits(user_id: int) -> int
```

- `consume_credits`: `cost <= 0` 방어(음수 차감=크레딧 증가 악용 차단) → False.
- `add_credits`: `plan='lab'`은 승격 대상 아님(면제 유지). free/pro만 pro로.

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

### `POST /deck/upload` (deck.py:69-91)
```
require_can_author(user)                        # 무료 소진 or 유료 잔액부족 → 402(조기)
...
charged_credits = 0
if should_consume_free_deck(user):              # free 플랜 (기존)
    if not consume_free_deck(...): raise author_gate_error
elif author_charges_credits(user):              # 유료(pro)
    if not consume_credits(user_id, DECK_COST): raise credit_low_error
    charged_credits = DECK_COST
# charged_credits를 run_authoring_pipeline 인자로 전달 (환불 추적)
```
- 선차감(job 생성 전, 레이스 방어) 유지. 파이프라인 ERROR → 환불.

### 파이프라인 실패 환불 (`pipeline._log_done`, 기존 `refund_free_deck` 옆)
- **환불 추적 = 명시 인자.** 소비 시점의 plan을 나중에 재판정하면 그 사이 충전/강등으로 틀어질 수 있다.
  업로드 핸들러가 실제 차감한 것을 `run_authoring_pipeline(..., charged_credits: int)`로 넘긴다.
  - `charged_credits == 0` → (무료 카운터 소비 또는 면제) 기존 `refund_free_deck` 경로 판정 그대로.
  - `charged_credits > 0` → ERROR 시 `refund_credits(user_id, charged_credits)`.
- 무료 카운터 환불(`refund_free_deck`)과 크레딧 환불은 **상호배타**(한 업로드는 둘 중 하나만 선차감).

### `POST /deck/{id}/nlpatch`·`/nlpatch/propose` (deck.py:159, 196)
```
require_can_ai_designer(user)                   # free→402(게이트), pro→잔액검사
if plan=='pro' and not _is_exempt:
    if not consume_credits(user_id, AIEDIT_COST): raise credit_low_error
# LLM 호출 실패 시 환불(호출 전 차감이면 try/except로 refund)
```
- AI 편집은 **호출당 차감**. LLM 실패(에러)면 환불.

### export (변화 없음)
`require_can_export`만. 크레딧 미차감.

## 8. API 표면

```
GET /api/me/credits → {credits: int, plan: str}
```
- 프론트 잔액 위젯(P1-2) 준비. 게이트 아님(읽기).
- **충전 엔드포인트는 이 스펙 밖**(Creem 웹훅 붙일 때). 지금은 `add_credits` 함수 + 관리자/테스트 수동 충전으로 충분.

## 9. 에러 처리

- `ERR-CREDIT-LOW`(402): 유료 유저 잔액 부족. 프론트 → "충전" CTA.
- `ERR-PLAN-AUTHOR`(402, 기존): 무료 1덱 소진. 프론트 → "업그레이드/충전" CTA.
- `consume_credits` 실패는 예외 아님(False 반환) → 호출부가 402로 변환(레이스 방어 일관).
- 음수/0 cost 방어(악용 차단).

## 10. 테스트 (TDD, `backend/tests/`)

신규 `test_credits.py`:
- `consume_credits`: 잔액충분→차감·True / 부족→불변·False / cost≤0→False / **동시 2건**(원자성, 하나만 성공).
- `refund_credits`: 가산. `add_credits`: 가산+plan승격, lab은 승격 안 됨.
- 게이트: 무료 1덱 후 생성 차단(ERR-PLAN-AUTHOR) / 유료 생성 시 DECK_COST 차감 / 잔액부족 402(ERR-CREDIT-LOW) / AI편집 AIEDIT_COST 차감 / **export 무과금**(크레딧 불변) / lab·service 면제(차감 0).
- 실패 환불: 파이프라인 ERROR → 선차감 크레딧 복구.

기존 `test_free_trial.py` 회귀: 무료 경로 불변 확인.

## 11. 범위 밖 (명시)

- **Creem 결제/웹훅** — 충전은 `add_credits` 함수까지. 실결제는 Creem 키(세훈) 후 별도.
- **거래내역(ledger) 테이블·사용내역 UI** — P1-2.
- **잔액 위젯·소모량 뱃지 프론트** — P1-2(이 스펙은 `GET /me/credits`까지).
- **발행(publish) 크레딧** — Phase 2(Meta 심사).
- 단가 최종값 캘리브레이션 — 상수만 두고 나중 조정.

## 12. docs/ 반영 (구현 시)

헌법 "docs 먼저": 구현 착수 시 `docs/contracts/07_api_data_model.md`에 크레딧 스키마·차감 규칙·`GET /me/credits`·`ERR-CREDIT-LOW` 반영(v2.9). 이 브레인스토밍 스펙과 계약 문서는 별개 — 계약 문서가 정본.
