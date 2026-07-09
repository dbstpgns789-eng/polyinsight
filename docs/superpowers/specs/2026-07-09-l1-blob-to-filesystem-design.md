# L1 — BLOB → 파일시스템 (Storage 경계) 설계

> PolyInsight | 2026-07-09 · 운영 아키텍처 사다리 L1
> 상위 맥락: `docs/contracts/24_system_architecture.md` §4 (마이그레이션 사다리)

---

## 0. 한 문단 요약 (쉬운 말)

지금 카드 그림·ZIP·업로드 이미지·프로필 사진을 **데이터베이스(DB) 안**에 넣고 있다.
DB는 원래 짧은 글자(이름·날짜·상태)를 넣는 서랍장인데 무거운 파일까지 쑤셔넣어 뚱뚱하다 →
**백업이 무겁고 느리다.** L1은 이 무거운 파일들을 **일반 폴더**로 빼고 DB엔 **"어디 있다"는 주소만**
남긴다. 파일을 맡기고 찾는 일은 **단일 창구(Storage)** 하나를 거치게 해서, 나중에 저장 위치를
내 폴더 → 인터넷 창고(R2)로 바꿀 때 **창구 뒤편만 갈아끼우면** 되게 한다(L5).

---

## 1. 문제와 목표

### 현재 (실측 2026-07-09, `core/db.py`)
무거운 바이너리가 전부 SQLite BLOB 컬럼에 산다:

| 테이블 | BLOB 컬럼 | 성격 | TTL |
|---|---|---|---|
| `card_images` | `png_bytes` | 카드 PNG (렌더마다 갱신, 뜨겁고 무거움) | 24h |
| `exports` | `zip_bytes` | 내보내기 ZIP | 24h |
| `deck_assets` | `bytes` | 유저 업로드 이미지 (≤8MB) | 없음(영구) |
| `researchers` | `photo_bytes` | 프로필 사진 | 없음(영구) |

**약점**: DB 뚱뚱 → 백업/복제 무겁다. 파일과 메타데이터가 한 파일에 섞여 있다.

### 목표
- 무거운 파일을 **파일시스템**으로 이주, DB엔 **`storage_key`(주소 문자열)만** 남긴다.
- 파일 입출력을 **단일 Storage 창구** 뒤로 숨긴다 → L5(→Cloudflare R2)를 "박스 교체"로 만든다.
- **완료 조건**: 업로드→렌더→서빙→export 라운드트립이 디스크 경유로 실동작 · 영구 파일
  (`deck_assets`·`researchers`) 유지 · pytest green(신규 storage 테스트 포함).

### Non-goals (이번에 안 함)
- R2/오브젝트 스토리지 실전환(그건 L5). 이번엔 로컬 파일시스템 구현 하나만.
- 워커 분리·큐(L2). 저작·렌더 실행 위치는 그대로.

---

## 2. 결정 (사용자 확정 2026-07-09)

- **범위 = 4개 BLOB 전부** 이주 (영구 파일 `deck_assets`·`researchers` 포함).
  → 영구 데이터가 있으므로 **일회성 데이터 이주 스크립트** 필요.
- **전환 = 하드 컷오버** — 이주 전 DB 백업 → 스크립트로 전부 디스크로 → BLOB 컬럼 제거.
  임시 이중경로(읽기-통과) 코드는 만들지 않는다(L0에서 청소한 이중살림 냄새 회피).
- **정황 이점**: 배포 미실행(메모리 `project_lab_deployment`) → 현재 DB는 로컬 dev,
  기존 BLOB은 대부분 버려도 되는 테스트 데이터라 컷오버 리스크가 낮다.

---

## 3. 컴포넌트 설계

### 3-1. Storage 창구 — `backend/core/storage.py`

```python
class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> None
    async def get(self, key: str) -> bytes | None      # 없으면 None
    async def delete(self, key: str) -> None            # 없어도 조용히 통과
    async def delete_prefix(self, prefix: str) -> None  # job 통삭제용
```

- **async 시그니처가 핵심.** 파일 IO 자체는 동기지만 `asyncio.to_thread`로 감싸 이벤트 루프를
  막지 않는다(8MB 쓰기 대비). 이 async 계약 덕에 나중에 R2(네트워크 IO) 구현이 같은 시그니처로
  그대로 끼워진다 — 이게 L5를 싸게 만드는 유일한 이유.
- `get_storage()` 싱글톤 접근자(`core/db.py`의 연결 패턴과 동일 결).

### 3-2. FilesystemStorage 구현 (같은 파일)

- 루트 = `settings.STORAGE_DIR` (기본 `backend/var/blobstore`). `.gitignore`에 추가.
- `put`: 부모 디렉토리 생성 후 파일 쓰기(`to_thread`). `get`: 읽기 or None. `delete`: 있으면 unlink.
  `delete_prefix`: 해당 하위 디렉토리 `rmtree`.
- **키 안전성**: 키를 루트에 합칠 때 정규화하여 `..` 탈출 차단(키는 앱이 생성하지만 방어).

### 3-3. 키 스킴

```
jobs/{job_id}/cards/{card_num}.png
jobs/{job_id}/exports/{export_id}.zip
jobs/{job_id}/assets/{asset_id}
researchers/{sha16(name)}            # 이름에 유니코드/공백 → 16자 해시로 안전화
```

job 하위를 한 접두사로 묶어, `delete_job` 시 `delete_prefix(f"jobs/{job_id}")` 한 번으로
카드·export·asset 파일을 전부 정리한다.

---

## 4. DB 변경 (`core/db.py`)

### 스키마
4개 BLOB 컬럼 → `storage_key TEXT`.
- 신규 DB: 처음부터 `storage_key`로 `CREATE TABLE`.
- 기존 dev DB: `ALTER TABLE ... ADD COLUMN storage_key TEXT` (컬럼 존재 여부 가드로 idempotent).
- 데이터 이주(§5) 완료 후 BLOB 컬럼 제거(SQLite 3.35+ `DROP COLUMN`; 미지원 시 테이블 재생성).

### 함수 라우팅 (계약 시그니처는 최대한 보존)
- `save_card_image(job_id, card_num, png_bytes)`: `storage.put(key, png_bytes)` → 행에 `storage_key` upsert.
- `get_card_images(job_id)`: 행(`card_num`, `storage_key`, `expires_at`) 읽고 `storage.get`으로 dict 구성.
- `save_export`/`get_export`, `save_deck_asset`/`get_deck_asset`/`list_deck_assets`,
  `researchers` 사진 함수 동일 패턴.
- `delete_job`: 행 삭제 후 `storage.delete_prefix(f"jobs/{job_id}")`.
- `delete_card_images_above`, TTL 클린업(`delete_expired`): 삭제 대상 행의 **파일도** `storage.delete`.

> 라우터(`routers/deck.py`·`export.py`·`images.py`)는 이미 `db.*`만 부르므로 원칙적으로 무수정.
> `db.*`의 반환 형태(예: `get_card_images` → `{card_num: bytes}`)를 보존하는 것이 이 경계의 계약.

---

## 5. 데이터 이주 — `backend/scripts/migrate_blobs_to_disk.py`

일회성, 수동 실행, 백업 우선:
1. 대상 DB 파일을 `backups/`에 타임스탬프로 복사(되돌리기 보장).
2. 4개 테이블 각 행의 BLOB을 읽어 `storage.put(적절한 key)` → `storage_key` 세팅 → BLOB null.
3. 전 행 이주 확인 후 BLOB 컬럼 제거.
4. 이주 건수·바이트 로깅(무성 실패 금지).

운영 순서(하드 컷오버): 서버 정지 → 백업 → 스크립트 실행 → 새 코드 배포 → 서버 기동.
(현재는 로컬 dev라 사실상 dev DB 대상.)

---

## 6. 테스트

- `tests/test_storage.py`: put/get/delete/delete_prefix 라운드트립 · 미존재 키→None ·
  prefix 격리 · `..` 탈출 차단.
- 기존 db/api 테스트: 픽스처에 `STORAGE_DIR = tmp_path/'storage'` 주입 →
  카드/export/asset 저장·조회가 임시 디스크 경유로 통과하도록.
  (`test_api.py`의 `use_memory_db`, `test_events`·`test_security_hardening` mem_db 픽스처.)
- 이주 스크립트 테스트: 구스키마 BLOB 행 심음 → 이주 실행 → 파일 존재 + `storage_key` 세팅 +
  BLOB 제거 검증.

---

## 7. 되돌리기 / 단방향 문

- Storage는 async라 파일은 additive. 코드 실패 시 커밋 revert.
- **유일한 단방향 요소 = BLOB 컬럼 drop.** DB 백업(§5-1)이 이를 보장 → 백업 복원으로 원복.
- STORAGE_DIR는 설정값 → 위치 변경 자유(양방향 문).

---

## 8. 변경 이력

| 날짜 | 요약 |
|---|---|
| 2026-07-09 | 신규. L1 설계 — Storage 창구 + 4 BLOB 디스크 이주(하드 컷오버). 사다리 §4 L1 구현 근거. |
