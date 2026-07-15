# L1 — BLOB → 파일시스템 (Storage 경계) 설계

> PolyInsight | 2026-07-09 · v1.1 (적대 진단 반영) · 운영 아키텍처 사다리 L1
> 상위 맥락: `docs/contracts/24_system_architecture.md` §4 (마이그레이션 사다리)
> v1.1 변경: 27-에이전트 적대 진단(17 확정) 반영 — 범위 3개로 축소(researchers 유령/제외),
> deck_assets 30일TTL 정정, 원자적 쓰기·정확 키계약·파일 백업·docs-먼저·무상태 storage 추가.

---

## 0. 한 문단 요약 (쉬운 말)

지금 카드 그림·ZIP·업로드 이미지를 **데이터베이스(DB) 안**에 넣고 있다. DB는 원래 짧은 글자(이름·
날짜·상태)를 넣는 서랍장인데 무거운 파일까지 쑤셔넣어 뚱뚱하다 → **백업이 무겁고 느리다.** L1은
이 무거운 파일들을 **일반 폴더**로 빼고 DB엔 **"어디 있다"는 주소(storage_key)만** 남긴다. 파일을
맡기고 찾는 일은 **단일 창구(Storage)** 하나를 거치게 해서, 나중에 저장 위치를 내 폴더 → 인터넷
창고(R2)로 바꿀 때 **창구 뒤편만 갈아끼우면** 되게 한다(L5).

---

## 1. 문제와 목표

### 현재 (실측 2026-07-09, `backend/core/db.py` HEAD)
무거운 바이너리가 SQLite BLOB 컬럼에 산다. **진단 결과 실사용은 3개, 1개는 유령:**

| 테이블 | BLOB 컬럼 | 성격 | TTL(실측) | L1 범위 |
|---|---|---|---|---|
| `card_images` | `png_bytes` | 카드 PNG (렌더마다 갱신, 뜨겁고 무거움) | 24h | ✅ 이주 |
| `exports` | `zip_bytes` | 내보내기 ZIP | 24h | ✅ 이주 |
| `deck_assets` | `bytes` | 유저 업로드 이미지 (≤8MB) | **30일**(`ttl_hours=24*30`, db.py:391) | ✅ 이주 |
| `researchers` | `photo_bytes` | 프로필 사진 | — | ❌ **제외(유령)** |

> **researchers.photo_bytes = 유령 컬럼.** `CREATE TABLE`(db.py:92-96)에만 존재하고 이 컬럼을
> **읽거나 쓰는 함수·라우터가 backend 전역에 하나도 없다**(save/get researcher 없음, `delete_job`도
> 미포함). 데이터 유입 경로 자체가 없다. → **L1 이주 범위에서 뺀다.** 스키마 컬럼은 그대로 두되
> (향후 프로필 기능 도입 시 그때 storage_key로 신설), 이주 스크립트·테스트 대상 아님.
> (models.py의 `CardMeta.researcher`는 이름 문자열 필드로 이 테이블과 무관.)

**약점**: DB 뚱뚱 → 백업/복제 무겁다. 파일과 메타데이터가 한 파일에 섞여 있다.

### 목표
- **실사용 3개 BLOB**(card_images·exports·deck_assets)을 파일시스템으로 이주, DB엔 `storage_key`만.
- 파일 입출력을 **단일 Storage 창구** 뒤로 숨긴다 → L5(→Cloudflare R2)를 "박스 교체"로.
- **완료 조건**: 업로드→렌더→서빙→export 라운드트립이 디스크 경유 실동작 · 편집/자가치유 재렌더의
  동시 쓰기에도 **찢어진 파일 없음** · pytest green(신규 storage 테스트 포함) · DB에 BLOB 컬럼 없음.

### Non-goals (이번에 안 함)
- R2/오브젝트 스토리지 실전환(L5). 이번엔 로컬 파일시스템 구현 하나.
- 워커 분리·큐(L2). 저작·렌더 실행 위치 그대로.
- researchers 프로필 사진 기능 신설(별건).

---

## 2. 결정 (사용자 확정 2026-07-09)

- **범위 = 실사용 3개 BLOB** 이주 (`researchers` 유령 컬럼 제외 — 진단 정정).
  deck_assets가 30일 TTL이나 유저 업로드 원본이라 재생성 불가 → **영구성 있는 유일 대상**으로 취급.
- **전환 = 하드 컷오버** — 이주 전 DB 백업 → 스크립트로 전부 디스크로 → BLOB 컬럼 제거.
  임시 이중경로(읽기-통과) 코드는 만들지 않는다(L0에서 청소한 이중살림 냄새 회피).
- **정황 이점**: 배포 미실행(memory `project_lab_deployment`) → 현재 DB는 로컬 dev,
  기존 BLOB 대부분 버려도 되는 테스트 데이터라 컷오버 리스크 낮다.

---

## 3. 컴포넌트 설계

### 3-0. 작업 목록 (컴포넌트/스텝)
1. **docs 먼저**(§8): `07_api_data_model.md`·`04_architecture.md`의 BLOB 스키마 → storage_key 반영.
2. `config.Settings`에 **`STORAGE_DIR` 필드 추가** (기본 `backend/var/blobstore`, `.env` override).
3. `backend/core/storage.py` 신설 (Storage 프로토콜 + FilesystemStorage, **무상태·원자적**).
4. `backend/core/db.py`: 3개 BLOB 컬럼 → storage_key, save/get 함수 storage 라우팅, TTL·삭제 경로.
5. `backend/scripts/migrate_blobs_to_disk.py` (백업 우선, **멱등**).
6. `backup_db.py`(또는 신규): STORAGE_DIR 영구 프리픽스 백업 확장 (§7).
7. `.gitignore`에 `backend/var/`(blobstore) 추가.
8. 테스트(§6).

### 3-1. Storage 창구 — `backend/core/storage.py`

```python
class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> None      # 원자적(temp+replace)
    async def get(self, key: str) -> bytes | None            # 없으면 None
    async def delete(self, key: str) -> None                 # 없어도 조용히 통과
    async def delete_prefix(self, prefix: str) -> None       # job 통삭제용
```

- **async 시그니처가 핵심.** 파일 IO는 `asyncio.to_thread`로 감싼다(8MB 쓰기가 이벤트 루프 안 막게).
  이 async 계약 덕에 나중에 R2(네트워크 IO) 구현이 같은 시그니처로 그대로 끼워진다 — L5를 싸게 만드는 이유.
- **무상태 접근자** `get_storage()`: **인스턴스/경로를 캐시하지 않고** 매 호출 `settings.STORAGE_DIR`를
  라이브로 읽는다. (진단: db.py의 `_db_path()`가 매 호출 `settings.DATABASE_URL`를 라이브 read하는
  바로 그 패턴 — 이 무캐시 속성이 테스트 격리(monkeypatch로 tmp 주입)를 성립시킨다. "싱글톤"이면 첫
  호출값을 캐시해 테스트 오염 → 금지.)

### 3-2. FilesystemStorage 구현 (같은 파일)

- 루트 = `settings.STORAGE_DIR` (기본 `backend/var/blobstore`). **프로덕션은 레포 밖 마운트 볼륨으로
  `.env` override** (예: `/var/lib/polyinsight/blobstore` — `24_system_architecture.md` §4 "호스트 디스크 볼륨"과 정합).
- **`put`은 원자적**: 같은 디렉토리의 임시파일에 쓰고 `os.replace(tmp, dest)`로 rename (POSIX·Windows
  모두 동일 파일시스템 내 rename 원자적). 부모 디렉토리 없으면 생성.
  → 두 재렌더가 같은 결정적 키에 동시에 써도 찢어진(torn) 파일이 안 남는다(§ 회귀 방지, 아래).
- `get`: 읽기 or None. `delete`: 있으면 unlink(없어도 통과). `delete_prefix`: 하위 디렉토리 `rmtree`.
- **키 안전성**: 루트에 합칠 때 정규화하여 `..` 탈출 차단(키는 앱이 uuid로 생성하지만 방어).
- **에러 정책**: `put`이 `OSError`(ENOSPC 디스크풀·EACCES 권한 등)를 던질 수 있다 →
  호출부에서 삼키지 말고 표면화: 렌더 경로는 이미 카드별 try/except로 warning 강등(`deck_renderer.py:126-129`),
  **업로드 라우터(`upload_deck_asset`)는 try/except 추가**해 500 대신 명확한 에러코드 반환.

### 3-3. 키 스킴

```
jobs/{job_id}/cards/{card_num}.png     # 결정적 키(재렌더 시 덮어씀 → 고아 안 생김)
jobs/{job_id}/exports/{export_id}.zip  # export_id=uuid → 재시도 시 새 키
jobs/{job_id}/assets/{asset_id}        # asset_id=uuid16 → 재시도 시 새 키
```

job 하위를 한 접두사로 묶어, `delete_job` 시 `delete_prefix(f"jobs/{job_id}")` 한 번으로
카드·export·asset 파일을 전부 정리한다.

---

## 4. DB 변경 (`backend/core/db.py`)

### 스키마
3개 BLOB 컬럼(`card_images.png_bytes`·`exports.zip_bytes`·`deck_assets.bytes`) → `storage_key TEXT`.
- 신규 DB: 처음부터 `storage_key`로 `CREATE TABLE`.
- 기존 dev DB: `ALTER TABLE ... ADD COLUMN storage_key TEXT` (컬럼 존재 가드로 idempotent).
- 데이터 이주(§5) 완료 후 BLOB 컬럼 `DROP COLUMN` (런타임 sqlite 3.45.3 ≥3.35 확인 — 지원됨).
- `researchers.photo_bytes`는 **손대지 않음**(유령, 범위 밖).

### 함수 라우팅 — **반환 dict 키 계약을 보존**(진단: 라우터·에이전트가 BLOB 키를 직접 읽음)
라우터·에이전트가 db 반환 dict의 **BLOB 키를 직접 역참조**한다. 컬럼만 리네임하면 즉시 깨진다.
db 함수가 `storage.get` 결과를 **같은 키 이름**으로 재조립해야 "호출부 무수정"이 성립한다:

| db 함수 | 반환 형태(보존) | 직접 소비자 |
|---|---|---|
| `get_card_images(job_id)` | `{card_num: bytes}` | `deck.py:get_deck_card`, self-heal `_heal_card_images`, `export.py:get_card_image` |
| `get_export(id)` | `dict`에 **`zip_bytes`** 키 = `await storage.get(key)` | `export.py:download_zip` (`row['zip_bytes']`) |
| `get_deck_asset(job_id, asset_id)` | `dict`에 **`bytes`**(+`mime`) 키 = `await storage.get(key)` | `deck.py:get_deck_asset`, `deck_renderer.py:_inline_deck_assets` (`asset['bytes']`) |

- `SELECT *`(get_export)·`SELECT ...bytes...`(get_deck_asset) 를 `storage_key` SELECT로 바꾸고 dict를 손수 구성.
- `save_card_image`/`save_export`/`save_deck_asset` = `storage.put(key, data)` → 행에 `storage_key` upsert.
- **주의**: 라우터 3개 중 `images.py`는 BLOB 무관(Pexels/Unsplash 검색만) — 대상 아님. 실제 BLOB
  소비자는 `deck.py`·`export.py` 라우터 + `deck_renderer.py`(에이전트, db.* 경유).

### 삭제·TTL 경로 (파일도 지운다)
- `delete_job`: 행 삭제 후 `storage.delete_prefix(f"jobs/{job_id}")`.
- `delete_card_images_above(job_id, max_card_num)`: 삭제 대상 행의 `storage_key`를 **SELECT 후** 파일 삭제, 그다음 행 삭제.
- **TTL 클린업 = `cleanup_expired_blobs`**(진단: 스펙 초안의 `delete_expired`는 오타 — 실제 이름).
  현재 `card_images`·`exports`를 **행 열거 없이 벌크 DELETE**(db.py:577-586) → 파일도 지우려면 만료 행
  `storage_key`를 **먼저 SELECT** 후 `storage.delete`, 그다음 행 DELETE로 재구조화.
- **deck_assets 만료 처리(신규)**: 현재 `cleanup_expired_blobs`가 deck_assets를 **안 건드림**(기존 누락).
  30일 만료 자산 파일이 디스크 고아로 남지 않도록 **cleanup에 deck_assets 만료 행+파일 삭제를 추가**.

---

## 5. 데이터 이주 — `backend/scripts/migrate_blobs_to_disk.py`

일회성·수동·백업 우선·**멱등(재실행 안전)**:
1. 대상 DB를 `backups/`에 타임스탬프로 스냅샷(`backup_db.py` VACUUM INTO 재사용 — 되돌리기 보장).
2. 3개 테이블 각 행: `storage_key`가 이미 있으면 **skip**(멱등), 없고 BLOB 있으면 `storage.put` →
   `storage_key` 세팅 → BLOB null.
3. **전 행 이주 확인 후** BLOB 컬럼 `DROP COLUMN`(별 트랜잭션).
4. 이주 건수·바이트 로깅(무성 실패 금지).

운영 순서(하드 컷오버): 서버 정지 → 백업 → 스크립트 → 새 코드 배포 → 기동.
중간 실패 시: 최초 백업이 다른 타임스탬프로 보존되므로 원본 소스 생존 → 재실행(멱등) 또는 백업 복원.

---

## 6. 테스트

- `tests/test_storage.py`: put/get/delete/delete_prefix 라운드트립 · 미존재 키→None · prefix 격리 ·
  `..` 탈출 차단 · **원자성**(같은 키 동시 put 다수 → 온전한 한 파일만, torn 없음) · 미존재 파일 delete 무해.
- 기존 db/api 테스트: 픽스처에 `STORAGE_DIR = tmp_path/'storage'` 주입(무상태 접근자라 라이브 반영) →
  카드/export/asset 저장·조회가 임시 디스크 경유로 통과. (`test_api.py:use_memory_db`,
  `test_events`·`test_security_hardening` mem_db 픽스처에 STORAGE_DIR 추가.)
- 반환 키 계약 회귀 테스트: `get_export`→`zip_bytes`·`get_deck_asset`→`bytes`가 storage.get로 채워져
  `export.py` 다운로드·`deck_renderer` 인라인이 무손상.
- 이주 스크립트 테스트: 구스키마 BLOB 행 심음 → 이주 → 파일 존재 + `storage_key` 세팅 + BLOB 제거,
  **재실행 시 skip(멱등)** 검증. 실사용 3개 BLOB만(researchers 제외).

---

## 7. 백업 확장 (진단: L1이 파일 백업을 깸)

현재 `backup_db.py`는 **DB 파일만** 스냅샷(VACUUM INTO). L1 후 유저 업로드(deck_assets)가 DB 밖으로
빠지면 정기 백업에서 사라진다 → **재해 시 유저 데이터 백업 공백.**
- 백업 잡을 확장: **STORAGE_DIR의 영속 프리픽스(`jobs/*/assets/`)도 백업 대상**에 포함.
  (TTL 재생성 가능한 `cards/`·`exports/`는 제외 가능.)
- 복원 런북에 **파일 복원 단계** 추가.
- DB 스냅샷과 파일 스냅샷의 **시점 정합** 주의(storage_key는 DB, 파일은 디스크 → 어긋나면 dangling key).

---

## 8. docs 먼저 (계약 문서 반영 — 코드보다 선행)

> 헌법 루트 `CLAUDE.md §4·§6·§7`(docs-먼저) 준수. L0에서 배운 교훈(문서 표류) 반복 금지.

- `docs/contracts/07_api_data_model.md`: `deck_assets.bytes` 등 BLOB 스키마 표 → `storage_key` 갱신 + Storage 경계 서술.
- `docs/contracts/04_architecture.md`: `card_images.png_bytes`·`exports.zip_bytes` CREATE TABLE DDL(04:328,337) →
  `storage_key`로 갱신, 저장 경계(파일시스템 창구) 반영.
- 이 갱신을 **코드 커밋보다 먼저** 커밋.

---

## 9. 되돌리기 / 단방향 문

- Storage는 async·원자적이라 파일은 additive. 코드 실패 시 커밋 revert.
- **유일한 단방향 요소 = BLOB 컬럼 drop.** DB 백업(§5-1)이 보장 → 백업 복원으로 원복.
- 롤백은 **한 쌍**: DB 백업 복원 **+** 해당 코드 커밋 git revert(신 코드는 storage_key 컬럼 기대). 짝 필수.
- 고아 파일 처리: put 성공+행 커밋 실패 시 exports/assets에 고아 가능(결정적 키 card_images는 덮어써 무고아).
  `delete_prefix`(job 삭제)가 대부분 회수. 필요 시 참조 없는 파일 GC(향후, 무해).
- STORAGE_DIR는 설정값 → 위치 변경 자유(양방향 문).

---

## 10. 변경 이력

| 날짜 | 버전 | 요약 |
|---|---|---|
| 2026-07-09 | v1.0 | 신규. Storage 창구 + 4 BLOB 디스크 이주(하드 컷오버). |
| 2026-07-09 | v1.1 | 27-에이전트 적대 진단(17 확정) 반영. 범위 4→3(researchers 유령 제외)·deck_assets 30일TTL 정정·원자적 쓰기(temp+replace)·정확 반환키 계약·TTL 파일삭제 재구조화+deck_assets 만료청소·파일 백업 확장(§7)·docs-먼저(§8)·무상태 storage·config STORAGE_DIR 스텝·OSError 정책·프로덕션 경로 override·멱등 이주. |
