# 설계: 인스타그램 자동 발행 슬라이스 (Phase B 첫 조각)

- 작성일: 2026-07-22
- 상태: 설계 승인됨 (구현 계획 대기)
- 선행 스펙: `docs/superpowers/specs/2026-07-21-phase0-semi-auto-publish.md` (Phase 0 = 캡션·수동 export. Graph API/OAuth/원클릭 발행을 **"Phase 1+ OUT"**으로 명시 → **이 문서가 정확히 그 Phase 1**)
- 로드맵 맥락: 발행 전략 A→B 중 **B의 최소 발행 슬라이스**. Mirra식 풀스위트(예약·캘린더·멀티채널·DM·분석)는 전부 제외.

---

## 1. 목적 & 성공 기준

### 목적
완성된 논문 카드 덱 한 세트를, 앱이 유저의 인스타그램 비즈니스/크리에이터 계정에 **직접 캐러셀로 발행**한다. 이 슬라이스는 두 가지를 동시에 만족한다:
1. **Meta 앱 심사 언블록** — `instagram_business_content_publish` 권한을 실제로 호출하는 동작 = 시연영상 대상 + 심사 제출에 필요한 "30일 내 성공 API 콜" 이력.
2. **최소 유용 기능** — 유저가 수동 4동작(캡션복사·이미지다운·앱전환·붙여넣기) 없이 원클릭 발행.

### 성공 기준 (심사 통과 우선 = 최소)
- 연동된 IG 비즈니스 계정에 **실제 게시글(캐러셀)이 뜬다.**
- `로그인 → 덱 생성 → 인스타 연동 → 인스타에 올리기 → 게시됨`을 끊김 없이 시연 녹화할 수 있다.
- 제출 전 30일 내 `instagram_business_content_publish` 성공 콜 ≥ 1.
- 에러 복구·재시도 큐·상태 관리는 **최소** (실패 시 명확한 에러 메시지까지만). Meta 승인 후 반복 개선.

### 비목표 (이번 슬라이스 OUT)
예약 발행 · 콘텐츠 캘린더 · 멀티채널(틱톡/유튜브/쓰레드/X) · DM 자동응답 · 성과 분석 · 발행 후 편집 · 스토리/릴스 · 다중 IG 계정 · 자동 토큰 갱신 크론.

---

## 2. API 경로 결정: Instagram Login (신규)

**Instagram API with Instagram Login**을 쓴다 (Facebook Login 클래식 아님).

- 유저가 **인스타 계정으로 직접 연동** — 페이스북 페이지 불필요. 진입장벽 낮음.
- 요청 권한(scope): `instagram_business_basic`, `instagram_business_content_publish`.
- 발행은 `graph.instagram.com` 호스트 + IG 프로페셔널 계정 ID로 호출.
- 근거: 새 앱 권장 경로 + 유저가 FB 페이지를 안 가져도 됨.

> ⚠️ **구현 시점 재확인 필수**: Meta의 스코프명·엔드포인트·OAuth URL은 자주 바뀐다. 구현 착수 시 최신 Meta 공식문서로 스코프·호스트·플로우를 대조한 뒤 코딩한다. 아래 엔드포인트는 설계 시점 기준.

---

## 3. 컴포넌트 개요

```
[프론트] DeckExportModal "인스타에 올리기" 모드 확장
   │  (미연동) → "인스타 연동" → OAuth start
   │  (연동됨) → "자동 발행" → POST publish
   ▼
[백엔드]
   ① OAuth 연동      routers/auth.py  +  core/oauth.py   (instagram provider)
   ② 토큰 저장        core/db.py  social_accounts 테이블  +  core/crypto.py (암호화)
   ③ 공개 카드 URL     routers/deck.py  서명 capability 라우트
   ④ 발행 클라이언트    agents/deck/ig_publish.py  (Graph API 캐러셀)
   ⑤ 크레딧 카운터      core/db.py  users.credits  +  차감 로직
   ▼
[외부] graph.instagram.com  (media → media_publish)
```

각 조각은 독립 테스트 가능한 단위:
- OAuth 연동: "인스타 계정 붙이고 long-lived 토큰을 암호화 저장한다"
- 공개 URL: "서명+만료 검증되면 카드 PNG 바이트를 무인증으로 낸다"
- 발행 클라이언트: "공개 URL 리스트 + 캡션 → 캐러셀 게시글 permalink"
- 크레딧: "잔액 확인 → 성공 시 차감"

---

## 4. Instagram Login OAuth + 토큰 저장

### 연동 플로우 (앱 로그인과 분리)
유저는 이미 로그인 상태(이메일/구글). 인스타 연동은 **앱 세션을 만드는 게 아니라** 이미 로그인한 유저에 발행 권한을 붙이는 것.

- `GET /api/auth/oauth/instagram/start`
  - `get_current_user` 필요(로그인한 유저만 연동 가능).
  - `state`(CSRF, `secrets.token_urlsafe`) 발급 + `oauth_state` 쿠키(기존 패턴 재활용), IG authorize URL로 리다이렉트.
- `GET /api/auth/oauth/instagram/callback`
  - `state == cookie_state` 검증 → code 교환.
  - short-lived 토큰 → **long-lived 토큰(약 60일) 교환** → `social_accounts`에 upsert.
  - `/dashboard`(또는 연동 시작 지점)로 리다이렉트.

`core/oauth.py`에 `instagram_authorize_url(state)` / `instagram_exchange(code)` 추가. `redirect_uri(provider)`는 이미 `/api/auth/oauth/{provider}/callback`로 파라미터화됨 → 그대로.

### 신규 테이블: `social_accounts`
`core/db.py` `migrate()`에 idempotent `CREATE TABLE IF NOT EXISTS` 추가.

| 컬럼 | 타입 | 비고 |
|---|---|---|
| `user_id` | INTEGER FK→users | |
| `provider` | TEXT | `'instagram'` |
| `ig_user_id` | TEXT | IG 프로페셔널 계정 ID (발행 대상) |
| `ig_username` | TEXT | 표시용 |
| `access_token` | TEXT | **암호화 저장** (§4 암호화) |
| `token_expires_at` | TIMESTAMP | long-lived 만료 |
| `created_at` / `updated_at` | TIMESTAMP | |

- PK `(user_id, provider)` — 유저당 IG 1개 (YAGNI, 다중 계정 OUT).
- 헬퍼: `db.upsert_social_account`, `db.get_social_account(user_id, provider)`, `db.delete_social_account`.

### ★ 토큰 암호화 at-rest
세션/auth 토큰은 단방향 해시(sha256)로 충분했지만, **IG 토큰은 발행 때 되돌려 써야** 하므로 대칭 암호화.

- `core/crypto.py` — 대칭 암호화 헬퍼(예: Fernet/AES-GCM). `encrypt(plaintext) -> str`, `decrypt(token) -> str`.
- 키: `.env` `SOCIAL_TOKEN_KEY` (미설정 시 IG 연동 기능 dormant — 구글 OAuth의 dormant 패턴과 동일).
- 저장 시 암호화, 발행 직전 복호화. 로그·에러 메시지에 토큰 원문 절대 노출 금지.

---

## 5. 공개 카드이미지 URL (서명 capability URL — 확정: A안)

Meta `POST /media`는 쿠키 없이 서버가 직접 긁을 **공개 HTTPS `image_url`**을 요구한다. 현재 렌더 카드 PNG 라우트 3개는 전부 인증+소유자체크+24h 만료 → 공개 URL 0개.

### 채택: 우리 도메인 서명 capability URL
- 신규 라우트 `GET /api/deck/{job_id}/cards/{card_num}/public?exp=<unix>&sig=<hmac>`
  - `deck.router`는 per-route self-gate라 **글로벌 `get_current_user` 우회 가능** (기존 `deck_assets` 무인증 URL이 이미 이 패턴).
  - 검증: `sig == HMAC_SHA256(secret, f"{job_id}:{card_num}:{exp}")` (constant-time 비교) **그리고** `now < exp`. 실패 시 404.
  - 통과 시 카드 PNG 바이트 반환. 만료됐으면 저장된 HTML로 self-heal 재렌더(기존 authed 라우트 로직 재사용).
- URL 발급: **발행 액션 내부에서만**, 발행하는 소유자에 대해서만. 만료는 짧게(예: 10분, 발행 윈도만 커버). Meta가 수 초 내 긁고, IG가 자기 사본을 만들면 우리 URL은 만료돼도 됨.
- 서명 키: `.env` 서버 시크릿(신규 `PUBLIC_CARD_URL_SECRET` 또는 기존 서버 시크릿 재사용 — 구현 시 결정). `PUBLIC_BASE_URL`을 오리진으로 URL 조립.
- 신규 인프라 0 — 기존 `FilesystemStorage` + `PUBLIC_BASE_URL` 재활용.

### 기각: R2/S3 푸시
storage Protocol이 지원하나 신규 인프라·크레덴셜·비용. 심사우선+우리 규모엔 오버킬. (스케일 시 storage 백엔드 교체로 자연 전환 가능 — 지금 안 함.)

---

## 6. Graph API 발행 (`graph.instagram.com`)

`agents/deck/ig_publish.py` — 발행 클라이언트.

```
입력: ig_user_id, access_token(복호화), 공개URL 리스트[card1..cardN], caption
1. 카드마다:  POST /{ig-user-id}/media
              (image_url=공개URL, is_carousel_item=true, access_token)
              → item creation_id
2.            POST /{ig-user-id}/media
              (media_type=CAROUSEL, children=[id1..idN], caption, access_token)
              → carousel container id
3.            컨테이너 status 폴링: GET /{container-id}?fields=status_code
              status_code == FINISHED 될 때까지 (최대 N회, 간격 제한). 최소 구현.
4.            POST /{ig-user-id}/media_publish
              (creation_id=carousel container id, access_token)
              → published media id
5. permalink 조회: GET /{media-id}?fields=permalink → 반환
```

- **캐러셀 = 카드뉴스 자연 포맷**(스와이프). 단일 이미지가 아님.
- 캡션은 **기존 `GET /api/deck/{job_id}/caption`**(검증 통과 수치만, 미확인 수치 0) 그대로 사용 — 발행 순간 fidelity 해자를 유지.
- 폴백 언급: 캐러셀 컨테이너 처리가 까다로우면(폴링 타임아웃 등) 단일 이미지 발행이 더 최소지만, 제품 산출물이 다중 카드라 **캐러셀을 기본으로** 한다.
- 레이트리밋: IG 계정당 25 게시/24h — 최소 슬라이스엔 무관.

---

## 7. 크레딧 최소 카운터

- `users.credits` INTEGER 컬럼 추가 (idempotent `ALTER` migration, default 0).
- 상수 `PUBLISH_CREDIT_COST` (설계 제안값: 5 — **BM와 함께 튜닝**, config 상수라 변경 쉬움).
- 발행 액션: 잔액 `credits >= PUBLISH_CREDIT_COST` 확인 → **발행 성공 시에만 차감**(실패=차감 없음). 부족 시 403.
- ⚠️ 결제(Creem) 미구축이라 현재 크레딧은 **admin 수동 시드**(박사님·lab 계정). 충전 UX·결제는 별도(BM 로드맵).

---

## 8. 신규/변경 API 엔드포인트

| 메서드·경로 | 인증 | 동작 |
|---|---|---|
| `GET /api/auth/oauth/instagram/start` | 로그인 | IG OAuth 시작(state 발급·리다이렉트) |
| `GET /api/auth/oauth/instagram/callback` | 로그인 | code 교환·long-lived 토큰 저장·리다이렉트 |
| `GET /api/social/instagram/status` | 로그인 | `{connected: bool, username?: str}` |
| `DELETE /api/social/instagram` | 로그인 | 연동 해제(토큰 삭제) |
| `GET /api/deck/{job}/cards/{n}/public` | **무인증(서명)** | 서명·만료 검증 후 카드 PNG |
| `POST /api/deck/{job}/publish/instagram` | 로그인+소유자 | 연동·크레딧 확인 → 캐러셀 발행 → `{permalink}` |

---

## 9. 데이터모델 / 설정 변경 요약

- 신규 테이블: `social_accounts`.
- 신규 컬럼: `users.credits`.
- 신규 파일: `core/crypto.py`, `agents/deck/ig_publish.py`.
- 신규 `.env`: `INSTAGRAM_CLIENT_ID`, `INSTAGRAM_CLIENT_SECRET`, `SOCIAL_TOKEN_KEY`, (선택)`PUBLIC_CARD_URL_SECRET`. 전부 미설정 시 IG 연동 dormant.
- 프론트: `DeckExportModal` "인스타에 올리기" 모드 확장 + 연동상태 조회.

---

## 10. UI (기존 재활용)

- `DeckExportModal`의 "인스타에 올리기" 모드:
  - **연동됨** → "자동 발행" 버튼 → `POST publish` → 성공 시 permalink 링크 노출.
  - **미연동** → "인스타 연동" 버튼 → OAuth start.
- **수동 폴백 존치** — 기존 캡션복사+이미지다운+인스타 열기 경로는 그대로 둔다. 개인 계정(비즈니스 아님)·미연동 유저·연동 실패 시 사용. (Phase A "아무나 되는 수동 발행"을 없애지 않는다.)

---

## 11. 에러 처리 (심사우선 = 최소)

- 미연동 상태에서 발행 시도 → 명확한 안내(연동 유도).
- 개인 계정 등 발행 불가 → 에러 메시지 + 수동 폴백 안내.
- Graph API 실패(토큰 만료·컨테이너 실패·레이트리밋) → 원인 담은 에러 메시지 반환, **자동 재시도·큐 없음**.
- 폴링은 횟수 상한(무한 대기 금지).
- 크레딧 부족 → 403 + 안내.

---

## 12. 테스트 & 검증

- **유닛(목킹)**: Graph 클라이언트 목킹으로 발행 순서(container→publish)·크레딧 차감(성공만)·서명 생성/검증(만료·위조 거부)·토큰 암호화 왕복. 실 LLM/실 Graph 콜 없이 대부분 커버.
- **라이브 1회**: 실제 IG 비즈니스 테스트 계정에 실발행 — 이게 유일한 실콜이자 **심사 요건인 30일 콜**도 됨. (비용발생 실콜은 실행 전 허락.)
- **실물 검증**: 발행된 게시글이 실제로 IG에 뜨는지 permalink로 육안 확인 (코드 "성공"만으로 증명하지 않음 — 산출물 실물을 잰다).

---

## 13. Meta 앱 심사 체크리스트 연계

이 슬라이스가 완성되면 심사 준비물 중 코드 부분이 채워진다:
- ✅ 개인정보처리방침 URL (라이브)
- 🟡 데이터삭제 안내 URL (`feat/data-deletion-page`, 배포 대기)
- ⬜ 실제 발행 기능 (이 슬라이스)
- ⬜ 시연영상 (이 슬라이스 동작 후 촬영)
- ⬜ 30일 내 성공 API 콜 (§12 라이브 발행이 충족)
- ⬜ 비즈니스 인증 (세훈/박사님, 리드타임 2~7일 — 병렬로 일찍 신청)
- ⬜ privacy에 IG 데이터 항목 추가 (연동 시 "인스타 접근·유저 대신 게시" 명시)

---

## 14. 구현 착수 시 재확인 항목 (open items)

- Meta 최신문서로 스코프명·엔드포인트·OAuth URL 대조 (§2 경고).
- 서명 키를 신규 env로 둘지 기존 서버 시크릿 재사용할지 (§5).
- `PUBLISH_CREDIT_COST` 확정값 (§7, BM 튜닝).
- 컨테이너 폴링 상한·간격 구체값 (§6).
