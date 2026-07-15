# 후보 착수 전 위험대장 + 로드맵 (L0b · L2 · 배포)

> PolyInsight | 2026-07-09 · 사다리 후속 준비
> 출처: 5축 적대 진단 워크플로(41 에이전트, 240만 토큰) — **35 위험 확정·0 기각**.
> 상위 맥락: `docs/contracts/24_system_architecture.md`(사다리), L1 완료(커밋 2ca81e5).
> 목적: 동시 진행 중인 UI 작업이 끝나면 **후보 전부**(L0b·L2·배포) 착수 — 그 전에 위험을 진단하고 순서를 못박는다.

---

## 0. 요약 — 지금 상태의 진짜 그림

- **L1 코드 자체는 견고**(원자 put·반환키 계약 전면 커버·자가치유 무손상, 187 green).
- **그러나 L1은 "배포 아티팩트"에 전혀 반영 안 됨** → `docker-compose.yml`·`Dockerfile`·`.env.example`·런북이 L0/L1 이전 상태로 표류. **재배포 한 번에 유저 자산 전량 소실**(CRITICAL).
- **L2는 현재 코드 그대로는 불가능** — "웹=워커=한 프로세스, 인메모리 인자 전달"을 깊게 가정. 최소 2개 하드 블로커(입력 PDF 미영속·`recover_stale_jobs` 큐 몰살).
- **L0b는 저위험이나 테스트 커플링 3곳** 동시 처리 안 하면 스위트 red.
- **계약문서 4종이 코드보다 뒤처짐**(07이 삭제된 `/api/upload`를 현행으로 서술 등) — docs-먼저 위반 재발.

---

## 1. 위험대장 (확정 35건, 심각도순)

### 🔴 CRITICAL (3)
| # | affects | 위험 | 완화 |
|---|---|---|---|
| C1 | L2 | **입력 PDF가 어디에도 저장 안 됨** — `deck_upload`가 `pdf_bytes`를 in-process 인자로만 워커에 전달(`deck.py:69,80`). 워커가 별 프로세스면 job_id로 PDF 꺼낼 곳 전무 → DB-큐 성립 불가 | enqueue 전 PDF를 Storage(`jobs/{job_id}/input.pdf`)에 저장 + jobs에 `card_count·persona·style_direction` 컬럼 추가. L1 Storage 경계 위에 얹음 |
| C2 | L2 | **`recover_stale_jobs`가 startup에 PENDING/RUNNING 전량 ERROR**(`db.py:453`, `main.py:54`) — 웹 재시작마다 큐 전체 삭제 + 워커의 살아있는 잡 몰살 | 블랭킷 회수 폐기. `worker_owner`·`heartbeat_at` 도입, heartbeat 타임아웃 넘긴 RUNNING만 재큐, PENDING 불가침, 회수를 웹 startup서 분리 |
| C3 | deploy | **STORAGE_DIR가 볼륨에 안 걸림**(`docker-compose.yml:5-17`은 `/data`만 마운트, STORAGE_DIR 기본=레포 안 `backend/var/blobstore`) → 컨테이너 재생성 시 카드PNG·export·유저자산 전량 증발 | compose backend에 `STORAGE_DIR=/data/blobstore` + 볼륨 재사용, `.env.example`·런북 반영 |

### 🟠 HIGH (9)
| # | affects | 위험 | 완화 |
|---|---|---|---|
| H1 | deploy/L1 | 이주 스크립트 미실행 배포 → 기존 `deck_assets` 조용한 소실 | 런북 순서 강제(정지→백업→migrate→배포) + startup 잔여 BLOB 경고 가드 |
| H2 | L2 | `render_deck`가 웹 요청 경로 3곳서 직접 호출(`deck.py:40,124,154`) → L2 '렌더 CPU 격리' 반쪽 | 편집·자가치유 렌더도 큐로, 또는 L2 범위='파이프라인만 분리'로 명시·하향 |
| H3 | L2 | DB-큐 원자 클레임·enqueue 스키마 부재 → 다중 워커 중복 픽업 | `claim_job(worker_id)` 단일 트랜잭션 원자 클레임(rowcount 확인). 단일 워커로 시작 |
| H4 | deploy | 워커 전용 프로세스 진입점 부재(정책·migrate·ttl_cleaner가 웹 lifespan에만) | `worker.py` 엔트리포인트 신설, ttl_cleaner 소유권 명확화, compose web·worker 2서비스 |
| H5 | deploy/L1 | `_validate_prod_config`가 STORAGE_DIR 영속성 미검사(`main.py:33-46`) → 소실 함정이 fail-closed 게이트 통과 | prod 검증에 STORAGE_DIR sanity 추가 + 런북 E2E 'compose down/up 후 자산 잔존' |
| H6 | L2 | `recover_stale_jobs` 단일프로세스 전제 재확인(C2와 쌍) | C2와 동일 |
| H7 | deploy/docs | 배포 런북이 L0/L1 이전 상태 표류(STORAGE_DIR·이주·백업크론 부재) | 런북 개정(docs-먼저) |
| H8 | docs | **07이 삭제된 `/api/upload`를 현행 진입점으로 서술** + 현행 `/api/deck/*` 누락 | 07 §1-1 은퇴배너 + 현행 deck 본선 교체 |
| H9 | docs/L2 | **24 §2 '실측 현재'가 자기모순** — 삭제된 orchestrator/run_pipeline 인용 | 24 §2 As-Is를 실측(BackgroundTasks in deck.py·deck/ 단일경로)으로 정정 |

### 🟡 MEDIUM (12) — 주제별
- **L0b 삭제 커플링**: `S6Output`이 `test_degrade_telemetry`에, 고아 모델이 계약테스트 2종에 물림 → 모델+테스트 동시 삭제. `export_store.py` **전체 고아 모듈**(아무도 import 안 함).
- **L2 동시성 싱글톤**: `_job_semaphore`·`_replace_lock`·rate-limit 싱글톤이 프로세스 로컬 → 다중프로세스서 분열. SQLite WAL=단일 writer·공유FS 전제(크로스 호스트 불가).
- **L2 면적 2배**: 레거시 카드에디터가 **두 번째 in-process Playwright 렌더**(`s7_renderer`)를 물고 48 실잡 서빙 → L2 마이그레이션 면적 2배.
- **L1 잔여**: `upload_deck_asset` OSError 미처리(스펙 §3-2 미구현) → 디스크풀 시 500. pre-L1 볼륨 위 재배포 시 이주 누락.
- **배포**: 백업 자동화 미등록(schtasks/cron) + 컨테이너 비인지 경로.
- **조정**: conftest autouse DB격리 부재 → 다음 세션 신규 테스트 ambient DB 재의존 함정. feat가 origin/main보다 **143커밋** 앞섬(미머지 델타).

### ⚪ LOW (11) — 주제별
- **L0b 잔재**: 고아 S6 모델타입 + false-green 계약테스트 2종, `LLM_MODEL_ARCHITECT` 죽은 설정, `S8Input/Output` 고아, `researchers.photo_bytes` 유령 컬럼.
- **L1 잔여**: 고아 파일 GC 부재(put 성공+commit 실패 시, 저확률·스펙 수용).
- **L2 잔재**: usage 집계 ContextVar 단일태스크 전제, `_heal_locks` dict 무제한 증식, 레거시 kind 분기 산재, `RENDER_TOKEN`이 레거시 goto 경로만 보호(주 deck 렌더는 `set_content`).
- **조정**: 핫파일(config·db·models·deck.py) 다세션 동시편집 충돌면.

---

## 2. 로드맵 (착수 순서 — 싸고·전제되고·면적 줄이는 것 먼저)

> 원칙: docs-먼저 → 부채 청소로 L2 면적 축소 → 배포 안전(독립 가능) → L2 사전조건 → L2 본체.
> 각 Phase는 착수 시 brainstorming→writing-plans로 세부 TDD 계획을 뽑는다(이 문서는 전략 순서).

### Phase 0 — 계약문서 정합 (docs-먼저 · 싸고 즉시 · 나머지의 전제)
닫는 위험: **H8·H9·H7** + 문서표류 재발 차단.
- 07 §1-1: `/api/upload` 은퇴배너 + 현행 `/api/deck/*`(upload·status·export·card) 본선 반영.
- 24 §2 As-Is 자기모순 정정(삭제된 orchestrator 인용 제거, 실측 BackgroundTasks·deck/ 단일경로).
- 04/05 잔여 은퇴배너 점검. 배포 런북(`2026-06-15-lab-deploy-runbook.md`) 개정 항목 식별.
- **[DOCS] 커밋만.** 코드 0. 반나절.

### Phase 1 — L0b 부채 청소 (저위험 · L2 면적 축소)
닫는 위험: MEDIUM/LOW L0b군 + L2 면적 2배 완화.
- 고아 S6 모델타입(Architect·Writer·Storyboard·PaperDigest·Digest*·Understand·Mismatch·S6Input/Output·S8Input/Output) 삭제 **+ 커플링 테스트 3곳 동시**(test_s6_contracts·test_s6_digest_contracts·test_degrade_telemetry).
- `export_store.py` 고아 모듈 삭제. `LLM_MODEL_ARCHITECT` 죽은 설정 삭제.
- `researchers.photo_bytes` 유령 컬럼: 문서 표기(이미 됨) 유지, 삭제는 선택.
- **레거시 카드에디터 = 얼려서 보존(확정 §3)**: 데이터·보기·다운로드(get_cards·card image serve·export.py) **유지**, 편집·재렌더(patch_cards·trigger_export·s7_renderer write) **은퇴**. 은퇴 전 read/serve 경로가 write 경로에 안 얽혔는지 확인(외과 절제). L2 면적 반감.

### Phase 2 — 배포 안전 (배포 전 필수 · L2와 독립 가능)
닫는 위험: **C3·H1·H5·H4(부분)** + 백업.
- STORAGE_DIR 볼륨 마운트(compose `STORAGE_DIR=/data/blobstore` + 볼륨, Dockerfile, `.env.example`).
- `_validate_prod_config`에 STORAGE_DIR 영속성 sanity 체크.
- 이주 스크립트 배포 순서 강제 + startup 잔여 BLOB 경고 가드(H1).
- 백업 자동화 등록(schtasks/cron) + assets 백업(L1서 함수는 만듦).
- `upload_deck_asset` OSError 처리(L1 잔여 · 스펙 §3-2).
- 런북 E2E: `compose down/up 후 자산 잔존` 검증.

### Phase 3 — L2 사전조건 (큐 enqueue 전 반드시)
닫는 위험: **C1·C2·H3·H6·H2** + 동시성 싱글톤.
- **C1**: 입력 PDF + enqueue 파라미터(card_count·persona·style_direction) 영속화(Storage `input.pdf` + jobs 컬럼).
- **C2/H6**: `recover_stale_jobs` 재설계(worker_owner·heartbeat_at, PENDING 불가침, 웹 startup서 분리).
- **H3**: DB-backed 큐 원자 클레임 `claim_job(worker_id)`.
- `worker.py` 엔트리포인트 + lifecycle 정책 이동(H4).
- **H2**: `render_deck` 단일 진입점 통합 or L2 범위='파이프라인만' 명시.
- 동시성 싱글톤(`_replace_lock`·`_job_semaphore`)은 **단일 호스트 전제 문서화**(크로스호스트는 L4/L6로 연기).

### Phase 4 — L2 본체 (web/worker 분리)
- BackgroundTasks → enqueue. 워커 폴링 루프. compose web·worker 2서비스.
- 24 §4 사다리 L2 완료 표기. 배포 아티팩트·런북 반영.

---

## 3. 결정 (사용자 확정 2026-07-09)
1. **레거시 카드 에디터 = 얼려서 보존(freeze)** — 옛 잡의 데이터·보기·다운로드(read/serve)는 유지, **편집·재렌더(s7_renderer write 경로)는 은퇴**. "자료로써 보존"의 해석. → L2 면적 반감(두번째 in-process 렌더 경로 제거). Phase 1에서 처리.
2. **L2 범위 = 파이프라인 첫 생성만 큐로** — `run_authoring_pipeline`(논문→덱)만 워커/큐. 편집·자가치유 재렌더는 웹 잔존 허용(H2 트레이드오프 수용, L2 목표 '렌더 격리'는 첫 생성분만). 24 배포 절에 명시.
3. **배포 = 나중에** — Phase 2(배포 안전)는 **배포 직전**에 실행(지금 아님). STORAGE_DIR 볼륨·백업 등은 배포 시점에 묶어서. 단 그 전에 배포하면 자산 소실이므로 배포 트리거 시 Phase 2 필수 선행.

### 결정에 따른 순서 재정렬
- **지금 (UI 무관·저위험)**: Phase 0(문서 정합) + Phase 1(L0b 청소 **+ 레거시 카드에디터 freeze**: read/serve 유지, edit/s7-render 은퇴).
- **UI 완료 후**: Phase 3(L2 사전조건) → Phase 4(L2 본체, 범위=첫 생성만).
- **배포 트리거 시**: Phase 2(배포 안전) 선행 필수.

---

## 4. 변경 이력
| 날짜 | 요약 |
|---|---|
| 2026-07-09 | 신규. 5축 적대 진단(35 위험 확정) → 위험대장 + Phase 0~4 로드맵. UI 작업 완료 후 착수 앵커. |
