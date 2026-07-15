# 연구실 배포 설계 — 무료 상시 호스팅 + 인증 + 행동 로깅

> v1.0 | 2026-06-15
> 대상: 박사님 1인 실유저 테스트 배포. 공공기관(KITECH) 환경.
> 톤: 의사결정 중심. Problem / Decision / Rationale / Risks.
>
> ⚠️ **SUPERSEDED (2026-07-13).** 이 설계는 2026-06-15 시점 기록(호스트=Oracle ARM, 앞문=Cloudflare Tunnel).
> 실제 배포는 **Azure VM + Caddy 자동 HTTPS + Azure 무료 호스트네임**(`polyinsight.japaneast.cloudapp.azure.com`)으로 라이브.
> 현행 배포·앞문·운영 정본 = `coo/OPERATIONS.md`. 이 문서는 역사 기록으로 보존.

---

## Problem

PolyInsight를 연구실에 배포해야 한다. 제약:

1. **무설치** — 공공기관 사용자에게 "실행환경 다운로드"를 요구할 수 없다. 브라우저 URL 하나로 끝나야 한다.
2. **무료 + 상시 가동** — 노트북을 24시간 켜두지 않아도 되어야 하고, 비용은 0원이어야 한다.
3. **모든 행동을 데이터로** — 박사님의 모든 행동(업로드·편집·파이프라인 실행·export)이 데이터로 남아야 한다.
4. **키 보호** — LLM API 키는 운영자(개발자) 키를 공유한다. 공개 URL에서 키가 무방비로 과금되면 안 된다.

### 코드에서 확인된 구조적 사실 (토폴로지를 결정함)

- **백엔드가 Playwright(헤드리스 Chromium)를 실행**한다(S7 렌더링). → Vercel·서버리스 불가. Chromium 포함 컨테이너 필요.
- **프론트↔백엔드 양방향 localhost 결합**:
  - FE→BE: `web/next.config.ts` rewrite `/api/*` → `localhost:8000`
  - BE→FE: `WEB_BASE_URL`로 백엔드 Playwright가 `localhost:3000` 렌더 라우트를 스크린샷
  - → 둘을 다른 호스트로 분리하면 상호 도달이 복잡. **단일 호스트가 압도적으로 단순.**
- **SQLite 로컬 파일**(`backend/core/config.py: DATABASE_URL=./polyinsight.db`). → 진짜 디스크가 있는 VM에선 영구 저장 가능.
- **인증은 UI만 존재, 백엔드 그린필드.** `web/src/app/login`·`signup` + `AuthForm`·`AuthLayout`(docs/15, docs/16)만 있고 백엔드 `auth` 라우터·세션·비밀번호 저장은 없음. 기존 라우터(`jobs`/`projects`/`export`)는 인증 무방비.
- 기존 로그인 UI에 "Google로 계속하기"·"비밀번호 찾기"가 있으나 모두 "추후 연결" 플레이스홀더.

---

## Decision

### 토폴로지 — 단일 호스트 + 무료 상시 VM + 터널

```
Oracle Cloud Always Free VM (Ampere ARM, 최대 4 OCPU / 24GB RAM, 영구 무료, 서울 리전)
  └─ Docker 컨테이너: Next.js(:3000) + FastAPI(:8000) + Playwright/Chromium
  │    · 둘은 localhost로 결합 (기존 구조 보존)
  │    · SQLite는 VM 디스크에 영구 저장
  └─ Cloudflare Tunnel (무료) → 고정 HTTPS URL → :3000 만 노출
```

- **노출은 터널이 Next.js(:3000) 한 포트만.** 브라우저→터널→Next, `/api/*`는 Next rewrite가 서버사이드로 localhost:8000에 프록시, 백엔드 Playwright는 localhost:3000 렌더. 8000은 외부 비노출.
- **인바운드 포트 개방 불필요** — 터널은 아웃바운드 연결. VM 방화벽은 SSH(22)만. 공격 표면 최소.
- 노트북 불필요, 상시 가동, 비용 0원.

### 인증 — 이메일/비밀번호 + 시드 계정 + 초대코드 가입

- 백엔드 신규 `auth` 라우터: 로그인(httpOnly 세션 쿠키), 로그아웃, argon2(또는 bcrypt) 비밀번호 해싱.
- **시드 스크립트**로 박사님 계정 1개를 직접 발급(가입 절차 없이 로그인 가능).
- **가입(signup)은 초대코드 게이트** — 기존 페이지 유지, 서버에서 초대코드 검증. 연구실 멤버 확장 시 코드 발급.
- 기존 `jobs`/`projects`/`export` 라우터에 **세션 검증 의존성/미들웨어** 적용.
- 프론트 `AuthForm`을 실제 엔드포인트에 배선 + `dashboard`/`editor` 라우트 가드.
- **v1 제외(스코프 컷):** Google 소셜 로그인, 비밀번호 찾기 → 버튼은 "준비 중" 비활성 또는 숨김.

### 행동 로깅 — 2레이어

1. **백엔드 `events` 감사 테이블(소스 오브 트루스)**: `user_id`, `event_type`, `timestamp`, `payload(JSON)`. 기록 대상 — 로그인/로그아웃, 업로드(논문 식별), **파이프라인 실행(S1–S8 stage 상태·degraded 여부·소요시간·토큰·비용)**, export(CRITICAL 무시 여부). 기록 헬퍼 1개로 통일.
2. **프론트 PostHog(행동 관찰)**: 클릭·편집·디자인세트 교체·체류시간 + **세션 리플레이**. `NEXT_PUBLIC_POSTHOG_*` env 게이트. 데이터 잔류 해외 OK 확인되어 Cloud 사용.

### LLM 비용 가드레일

- 실행당 토큰·비용을 `events`에 기록 → 누적 가시화.
- Anthropic/Gemini 콘솔에 **월 하드캡(usage limit)** 수동 설정.
- 키는 백엔드 env(`ANTHROPIC_API_KEY`)에만. 프론트 노출 0.

### 빌드 순서 (안전 우선)

```
인증 → 행동 로깅 → 비용 가드레일 → 컨테이너화 → Oracle 배포 → Cloudflare Tunnel
```

인증이 키 보호와 사용자 귀속의 토대이므로 1순위.

---

## Rationale

- **왜 Oracle Always Free인가:** "무료 + 상시 + Playwright 구동"을 동시에 만족하는 사실상 유일한 옵션. Render 무료는 잠들고 RAM 빠듯, Fly/Railway는 종량제, Vercel은 백엔드 불가, GCP e2-micro는 1GB로 Chromium엔 빠듯. Oracle ARM 24GB는 차고 넘치며 서울 리전 존재.
- **왜 단일 컨테이너인가:** FE↔BE가 localhost로 양방향 결합돼 있어 분리 시 상호 공개 URL 도달 문제가 생긴다. 한 박스에 두면 기존 결합·SQLite·로그가 그대로 산다. 0→이전 비용도 최소.
- **왜 Cloudflare Tunnel인가:** 무료 고정 HTTPS URL을 인바운드 포트 개방 없이 제공. SSL 관리 불필요. VM 공격 표면을 SSH만으로 축소. Phase 전환(노트북→VM→유료 PaaS) 시 터널 구성 재사용.
- **왜 이메일/비밀번호(소셜 제외)인가:** 1인 내부 사용자에게 Google OAuth는 동의화면 등록·리다이렉트 URI 등 과한 셋업. 시드 계정 + 초대 가입이 보안·확장성 균형. 공개 가입은 키 남용 위험이라 차단.
- **왜 SQLite 유지인가:** 단일 호스트 + 사용자 1명이면 단일 writer로 충분. Postgres 전환은 다중 사용자 시점에 재검토.

---

## Risks

| 리스크 | 영향 | 완화 |
|---|---|---|
| Oracle 가입 카드 본인확인 | 카드 없으면 진행 불가(실제 과금 X) | 사용자 확인 완료(Oracle 채택 결정) |
| ARM A1 용량 부족("out of capacity") | 인스턴스 생성 실패 | 재시도, OCPU 축소(2/12GB), AD 변경 |
| ARM64 Chromium 이미지 | 빌드 복잡도 | Playwright 공식 ARM 베이스 이미지 사용, 빌드 검증 |
| 유휴 인스턴스 회수(Oracle 정책) | VM 정지 가능 | 경량 부하 유지 / 모니터링 |
| 월 하드캡 수동 설정 | 미설정 시 키 무방비 | 배포 체크리스트에 필수 항목으로 |
| SQLite 단일 writer | 다중 사용자 시 경합 | 1명 무문제, 확장 시 Postgres |
| 세션 보안 | 탈취 위험 | HTTPS(터널) + httpOnly 쿠키, CSRF 기본 방어 |
| 노트북→VM 전환 아님(단일 대상) | 로컬 Windows 개발 단축경로 의존 불가 | Dockerfile은 Linux ARM 기준으로 작성 |

---

## Addendum — 렌더 토큰 우회 (2026-06-15 계획 중 발견)

기존 라우터를 세션으로 보호하면 **S7 렌더가 깨진다**: Playwright가 방문하는 Next `/render/{job}/{n}` 페이지가 `getCards()`로 `/api/cards/{job}`를 fetch하는데, 헤드리스 브라우저엔 세션 쿠키가 없어 401이 된다.

**결정:** 내부 서비스 우회 토큰 도입.
- `settings.RENDER_TOKEN`(랜덤 시크릿, 프로덕션 필수).
- `backend/agents/s7_renderer.py`의 Playwright 브라우저 컨텍스트에 `X-Render-Token` 헤더 주입(→ Next rewrite가 백엔드로 전달).
- `get_current_user`가 유효한 `X-Render-Token`이면 `role="service"`로 통과.
- 단일 프로세스라 백엔드 env와 렌더 컨텍스트의 토큰값이 자동 일치. `RENDER_TOKEN`이 빈 문자열이면 우회 비활성(보안 기본값).

## Out of Scope (v1)

- Google 소셜 로그인, 비밀번호 찾기 플로우
- Postgres 전환
- 유료 PaaS 이전(문서로만 — VM 장애/스케일 시 동일 컨테이너 이식 가이드)
- 다중 사용자 권한/역할(RBAC)
