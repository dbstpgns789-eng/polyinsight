# 운영 매뉴얼 — PolyInsight (Azure VM 배포·운영)

> PolyInsight | v1.0 · 2026-07-13 · 소유: COO(운영·서버·DB·회원·비용)
> 독자: **DevOps에 약한 1인 운영자**(근로장학생). 박사님(의뢰자) 파일럿 전달 대비.
> 출처: 6축 운영 진단 워크플로(13 에이전트) — 실제 스택(`docker-compose.yml`·`backend/Dockerfile`·`backup_db.py`·`config.py`·`main.py`) file:line 근거. 상위: `docs/contracts/24_system_architecture.md`(아키텍처), `docs/superpowers/plans/2026-07-09-candidates-risk-register-and-roadmap.md`(위험대장).
> **관리 규칙**: 인프라·설정 바꿀 때마다 이 문서 갱신. 아래 §11 열린 결정은 정하는 대로 이 문서에 박는다.

> 🔄 **2026-07-13 앞문 교체 — cloudflared 터널 → Caddy 리버스 프록시.** 공개 URL = **https://polyinsight.japaneast.cloudapp.azure.com**(Azure 공용 IP의 무료 DNS 호스트네임, 도메인 구매 없음). Caddy(image `caddy:2`)가 인바운드 **80·443**을 VM에서 직접 듣고 Let's Encrypt로 HTTPS를 자동 종단해 `web:3000`으로 프록시한다(설정=`deploy/Caddyfile` = `{$SITE_ADDRESS} { reverse_proxy web:3000 }`, `docker-compose.yml:37-51`). `TUNNEL_TOKEN` 폐기, `SITE_ADDRESS=polyinsight.japaneast.cloudapp.azure.com` 신규(caddy 필수). **보안 서사 변경**: NSG 인바운드 **22·80·443** 개방, VM 공용 IP(20.210.112.15) 인터넷에 직접 노출 — 옛 "웹 포트 0개·공격표면 SSH만·IP 은닉·Cloudflare DDoS 방어"는 **더 이상 참이 아님**. backend·web은 여전히 `expose`만이라 외부에서 닿는 건 Caddy(80/443)와 SSH(22)뿐. 아래 본문은 이 사실로 갱신됨.

---

## 0. 이 문서 쓰는 법 (제일 먼저)

DevOps 몰라도 되게 썼다. 상황별로 여기만 보면 된다:

- **처음 배포한다** → §1(지금 당장) + §6(배포) 순서대로.
- **매일/매주 뭐 하지?** → §2(운영 캘린더).
- **뭔가 터졌다** → §3(응급 런북)에서 증상 찾고 해당 섹션으로.
- **돈 걱정** → §5(비용).
- **박사님한테 넘기기 전 체크** → §1 + §10(보완 필요) + §11(네가 정할 것).

**우리 구조 한 줄**: Azure VM 한 대에 도커 컨테이너 3개(backend·web·caddy)가 돈다. 앞문은 **Caddy 리버스 프록시**라 VM이 인바운드 **80·443**을 직접 듣고 Let's Encrypt로 HTTPS를 종단해 `web:3000`으로 넘긴다. 공격 표면 = SSH 22 + 웹 80/443이고 **VM 공용 IP(20.210.112.15)가 인터넷에 직접 노출**된다(Cloudflare 은닉·DDoS 방어 없음). backend·web은 `expose`만이라 외부에서 직접 닿진 못한다. 데이터는 `/data` 볼륨(SQLite + 파일). LLM(Opus)이 유일한 진짜 변동비.

---

## 1. 지금 당장 할 것 (우선순위 — 배포 전 필수)

> 순서대로. 위 3개는 안 하면 **데이터 날림/돈 샘/못 뜸**이라 협상 불가.

- [ ] **1) STORAGE_DIR 볼륨 픽스 (C3 — 최우선)**. 지금 `docker-compose.yml`은 `/data`(SQLite)만 볼륨에 걸고, 파일저장(`STORAGE_DIR` 기본 `backend/var/blobstore`)은 컨테이너 임시 레이어에 떨어진다 → **재배포 한 번에 카드·유저 업로드 자산 전량 증발.** compose backend `environment`에 `STORAGE_DIR=/data/blobstore` 추가 → `docker compose down && up -d` 후 자산 살아남는지 웹에서 눈으로 확인. **모든 배포·백업의 선행조건.** (상세 §6)
- [ ] **2) 두 '돈 짐승'에 자동 상한·경보**. ⓐ Anthropic 콘솔에 **월 하드 스펜드캡 + 청구 경보**(오픈 가입발 변동비 폭탄 차단 — 유일한 자동 방어), ⓑ Azure 예산 **약 $80 + 50/80/100% 이메일 경보**(크레딧 소진 감시 = Oracle 이사 트리거). (상세 §5)
- [ ] **3) 자동 백업 cron 등록 + 복원 리허설 1회**. DB + L1 자산을 `/data/backups`(영속 볼륨)로 매일, 그 백업을 실제로 복원해 뜨는지 확인. **검증 안 된 백업은 백업 아님.** (상세 §8)
- [ ] **4) 앞문 잠그기**. SSH 키 로그인만(비번 off) + NSG 22를 **내 IP만**(80·443은 Caddy의 Let's Encrypt 검증·서비스용이라 전체 개방 유지) + fail2ban. `.env`의 `PUBLIC_BASE_URL`·`ALLOWED_ORIGINS`를 **반드시 https 공개 도메인**(`https://polyinsight.japaneast.cloudapp.azure.com`)으로 → prod 게이트 켜짐(둘 다 http면 공개 https 위에서 개발모드로 조용히 뜨는 함정). (상세 §4)
- [ ] **5) 이메일 (로그인은 안 막힘 — 오해 정정)**. 가입은 **이메일 인증 없이** 바로 됨(자동로그인→대시보드, grace 모드 비차단 — `auth.py:168`). 미인증의 실제 영향은 딱 2개: ⓐ **하루 업로드 3개 상한**(인증 시 20 — `ratelimit.py:76`), ⓑ 비번 분실 시 **자가 재설정 불가**(재설정 메일이 테스트모드라 안 감). → 파일럿엔 그냥 가입해 써도 되고(하루 3개), 상한 풀거나 비번사고 대비하려면 `seed_user`로 인증. 외부 정식 공개 때만 도메인 DKIM. (상세 §10-1)
- [ ] **6) 외부 업타임 모니터**. UptimeRobot 등으로 공개 URL 핑 → 이메일/푸시 경보. 단일 프로세스라 밤에 조용히 죽어도 아무도 모른다. (상세 §7)

---

## 2. 운영 캘린더 (뭘 언제)

| 주기 | 할 일 |
|---|---|
| **매일 18:00**(배포 창) | **일과 종료 배포** — 그날 머지된 코드 변경을 서버에 올린다. 절차 = §2-1. 코드 변경 없으면 건너뛴다 |
| **매일**(자동+눈) | 자동 백업(cron 03:00) 돌았나 로그 1줄 확인 · 업타임 모니터 초록인지 · (경보 오면만 대응) |
| **매주** | `docker compose ps`(3개 up) · `df -h`(디스크 여유) · **Anthropic 사용량**(console.anthropic.com — 급증=키유출/폭주 신호) · fail2ban 차단현황 · `run.log`서 로그인실패·rate limit 훑기 |
| **매월** | OS 보안패치(unattended-upgrades 자동) · Playwright/베이스 이미지 갱신 검토(`Dockerfile:3`) · `pip-audit`(의존성 취약점) · `.env` 밖-VM 사본 최신인지 · Azure 잔여 크레딧 확인 |
| **분기** | **복원 드릴**(백업을 실제로 새 위치에 복원해 뜨는지) · SSH 키/시크릿 로테이션 검토 · 크레딧 소진 예상 시 Oracle 이사 계획 |

---

## 2-1. 일과 종료 배포 (매일 18:00) — 확정 2026-07-15

> **왜 18:00인가**: 재배포는 **진행 중인 덱 생성 잡을 죽인다**(`recover_stale_jobs` 단일프로세스 전제, §5).
> 일과 종료 시각이 트래픽이 가장 한산하다. 여러 세션이 낮 동안 각자 커밋하므로, **하루치를 모아 저녁에 한 번** 올린다
> (= 변경 추적이 쉽고, 재시작으로 잡 죽이는 횟수가 하루 1회로 제한된다).

**절차** (코드 변경이 있는 날만):

```
1. 그린 확인 (로컬)         cd backend && pytest tests/  ·  cd web && npx tsc --noEmit && npx vitest run
2. 오늘 변경 훑기           git log --oneline --since="오늘 00:00"   (뭘 올리는지 눈으로)
3. GitHub 푸시             git push origin feat/emerald-redesign     ← Claude가 여기까지 대신 함
4. VM 접속·배포            ssh <VM> → cd <repo> && git pull && docker compose up -d --build   ← SSH 필요(사람)
5. 헬스 확인               docker compose ps (3개 Up) · logs backend에 "startup complete" · 공개 URL 자물쇠+랜딩
6. 유저 안내               재배포 중이던 덱 생성 잡은 실패 → 재생성 안내
```

- **Claude가 할 수 있는 것**: 1·2·3(그린 확인 + 오늘 변경 요약 + GitHub 푸시). **여기까지가 이 개발 머신의 한계다.**
- **사람이 해야 하는 것**: 4·5·6. VM(20.210.112.15)은 **이 머신에 SSH 키가 없어** Claude가 직접 못 친다.
  터미널에 SSH가 설정돼 있으면 `!ssh ...` 로 이 세션에서 돌릴 수 있다.
- **안전장치**: `STORAGE_DIR=/data/blobstore` 볼륨 픽스가 `docker-compose.yml:14`에 있어 **재배포해도 카드·유저 자산은 살아남는다**(위험대장 C3 해소). DB는 `/data` 볼륨.
- **배포 안 하는 날**: 문서·계획·메모리만 바뀐 날은 서버 코드에 영향 없음 → 건너뛴다.

---

## 3. 응급 런북 (터지면 여기부터)

| 증상 | 먼저 볼 것 | 상세 |
|---|---|---|
| **앱 접속 안 됨** | `docker compose ps` → 죽은 컨테이너 `logs` → 앞문/HTTPS 문제인가(`docker compose logs caddy` — 인증서·ACME) → `df -h`(디스크풀?) → 메모리(Chromium OOM?) | §7 |
| **덱 생성이 자꾸 실패/멈춤** | backend logs서 ERR-S1/S6/AUTHOR/RENDER · Chromium OOM(`MAX_CONCURRENT_JOBS` 낮춰) · **재배포/재시작 중이었나**(recover_stale_jobs가 진행 잡 몰살) | §7 |
| **Anthropic 청구 급증** | 콘솔 사용량 확인 → 키 유출 의심 시 즉시 revoke·교체 → 업로드 쿼터 낮추기(`UPLOAD_USER_LIMIT`) | §4-C, §5 |
| **데이터 날아감/복구 필요** | 최신 백업 찾기 → DB 복원 + assets tar **같은 시점 쌍**으로 → WAL/SHM 삭제 → 기동 → 로그인 확인 | §8 |
| **시크릿 유출 의심** | 해당 키 즉시 폐기·재발급(§4-C 표) → `.env` 교체 → 컨테이너 재기동 | §4-C |
| **backend가 자꾸 재시작(crash 루프)** | prod 게이트다 — `.env`에 `COOKIE_SECURE=True`·`PUBLIC_BASE_URL`·`RENDER_TOKEN` 빠졌나(`main.py:41-46`). 버그 아니라 방어 | §4, §6 |
| **VM이 통째로 죽음** | 새 VM 생성 → 도커 설치 → 백업 복원 → compose up (오프-VM 백업 사본 필수) | §8 |

> ⚠️ **공통 함정**: `docker compose restart`/재배포는 **진행 중인 덱 생성 잡을 죽인다**(`recover_stale_jobs` 단일프로세스 전제, `main.py:54`). 한산할 때 재배포하고, 유저에겐 실패한 덱 재생성 안내.

---

## 4. 보안

> 독자: DevOps에 약한 1인 운영자. "무엇을·언제·터지면 뭐"까지 그대로 따라 하면 되게 썼다.
> 우리 구조의 핵심 사실 한 줄: **앞문은 Caddy 리버스 프록시**다. Caddy가 VM에서 인바운드 **80·443**을 직접 듣고 Let's Encrypt로 HTTPS를 종단해 `web:3000`으로만 프록시한다(`docker-compose.yml:37-51`). backend·web은 여전히 compose 내부망에서만 보인다(`expose`만, 호스트 포트 없음 — backend `docker-compose.yml:17-18`, web `30-31`). 외부 공격 표면 = **SSH(22) + 웹(80/443)**, 그리고 **VM 공용 IP(20.210.112.15)가 직접 노출**된다(Cloudflare 은닉·DDoS 방어 없음 — 인터넷 봇이 IP를 스캔한다). 이 세 포트를 안 망치는 게 절반이다.

---

### 0. 5분 요약 — 우리 스택에서 보안의 실체

| 무엇 | 어디 | 현실 |
|---|---|---|
| 앞문 | Caddy(`caddy:2`) → `web:3000` (`docker-compose.yml:37-51`) | Caddy가 인바운드 **80·443**을 직접 수신. VM 공용 IP(20.210.112.15) **직접 노출**(Let's Encrypt가 이 IP로 도메인 검증, 봇이 스캔). Cloudflare 은닉·DDoS 방어 **없음** |
| TLS | Caddy(Let's Encrypt 자동) | HTTPS 종단이 VM 안의 Caddy 컨테이너. 인증서 자동 발급·갱신, `caddy-data` 볼륨에 영속(`docker-compose.yml:46`). 호스트에 nginx/certbot **설치 안 함** |
| 시크릿 | `.env` (VM 디스크, `env_file`로 주입 — `docker-compose.yml:10`) | `ANTHROPIC_API_KEY`(=진짜 돈), `RESEND_API_KEY`, `RENDER_TOKEN`, `GOOGLE_CLIENT_SECRET`. (`SITE_ADDRESS`는 시크릿 아님 — 공개 FQDN. `TUNNEL_TOKEN`은 폐기) |
| 앱 게이트 | `main.py:33-46` `_validate_prod_config` | 오리진에 `https://`가 보이면 `COOKIE_SECURE`·`PUBLIC_BASE_URL`·`RENDER_TOKEN` 없을 때 **기동 실패(crash)** — 의도된 방어 |
| 세션 | DB 저장 + 해시 | 별도 "세션 시크릿" 환경변수 **없음**. 토큰은 DB에 해시로. 만료 `SESSION_TTL_HOURS=72`(`config.py:39`) |
| 열린 포트 | SSH 22 + 웹 80·443 | 22는 키 로그인 + 내 IP만 + fail2ban. 80·443은 Caddy 앞문이라 전체 개방 유지(Let's Encrypt 검증에 필요) |

---

### A. 초기 설정 (1회 — 배포하는 날 순서대로)

#### A-1. `.env` 시크릿 관리

- [ ] `.env`가 git에 안 올라가는지 **먼저 확인** (이미 `.gitignore:15-17`에 `.env`·`*.env.*` 제외, `!*.env.example` 예외):
  ```bash
  cd ~/polyinsight
  git ls-files | grep -E '\.env'   # .env.example 만 나오면 OK. .env 나오면 사고(→ C 섹션)
  ```
- [ ] `.env` 권한을 나만 읽게 잠근다:
  ```bash
  chmod 600 ~/polyinsight/.env
  ls -l ~/polyinsight/.env   # -rw------- 확인
  ```
- [ ] `.env` **VM 밖 사본 1개** 보관(비밀번호 관리자 or 암호화 USB). VM 죽으면 시크릿도 죽는다.
- [ ] `.env`를 로그·스크린샷·채팅에 붙여넣지 않는다. 박사님 전달 시에도 값이 아니라 "어디에 뭐가 들어간다"만 공유.

#### A-2. SSH / VM 접근 (Azure)

- [ ] **SSH 키 로그인만, 비밀번호 로그인 끈다.** Azure VM을 SSH 공개키로 만들었으면 대개 이미 꺼짐. 확인·강제:
  ```bash
  sudo nano /etc/ssh/sshd_config
  #   PasswordAuthentication no
  #   PermitRootLogin no
  sudo systemctl restart ssh
  ```
  ⚠️ 재시작 전에 **새 터미널로 키 로그인 되는지 먼저 확인** — 안 그러면 나를 잠근다.
- [ ] **Azure NSG(네트워크 보안 그룹)** 인바운드 규칙:
  - [ ] 22(SSH)는 **내 집/사무실 IP만**(Source = My IP address). 전체(0.0.0.0/0) 금지.
  - [ ] **80·443은 전체(0.0.0.0/0) 개방** — Caddy 앞문이 여기로 트래픽을 받고, Let's Encrypt HTTP-01 챌린지가 80으로 들어와야 인증서가 발급된다. 닫으면 사이트가 안 열리거나 인증서 발급 실패.
  - [ ] 3000/8000은 **열지 마라.** web·backend는 `expose`만이라 Caddy 경유로만 닿는다. 호스트로 열면 우회·rate limit IP 위조 위험.
  - [ ] 확인: Azure Portal → VM → Networking → 인바운드에 **22·80·443**(+ 기본 Deny)만.
- [ ] **fail2ban 설치**(SSH 무차별 대입 자동 차단):
  ```bash
  sudo apt update && sudo apt install -y fail2ban
  sudo systemctl enable --now fail2ban
  sudo fail2ban-client status sshd
  ```

#### A-3. HTTPS / 앞문(Caddy) / prod 게이트

- [ ] HTTPS는 **Caddy가 처리** — VM 안 Caddy 컨테이너가 Let's Encrypt로 인증서를 자동 발급·갱신한다. 호스트에 nginx/certbot **설치 안 함**.
- [ ] `.env`에 `SITE_ADDRESS=polyinsight.japaneast.cloudapp.azure.com`(스킴 없는 맨호스트)를 넣는다 — caddy 서비스가 이 값으로 자동 HTTPS를 켠다(`docker-compose.yml:40`). NSG **80·443**이 열려 있어야 발급된다(A-2).
- [ ] `.env`에 아래 4개를 넣는다. **`ALLOWED_ORIGINS` 또는 `PUBLIC_BASE_URL`에 `https://`가 들어와야 prod 게이트가 켜진다**(`main.py:36-39`). ⚠️ **함정: 둘 다 http면 게이트가 아예 안 돌고, 공개 https 위에서 `COOKIE_SECURE=False`(개발 모드)로 조용히 뜬다.** 반드시 공개 도메인을 https로 넣어라:
  - [ ] `PUBLIC_BASE_URL=https://polyinsight.japaneast.cloudapp.azure.com` (인증메일 링크·OAuth 콜백 베이스도 이걸 씀 — `config.py:75-78`. Google OAuth를 켜면 `OAUTH_REDIRECT_BASE`도 같은 값)
  - [ ] `ALLOWED_ORIGINS=https://polyinsight.japaneast.cloudapp.azure.com` (CORS 심층방어 — `config.py:44`)
  - [ ] `COOKIE_SECURE=True` (`config.py:40`. 이게 켜지면 HSTS 헤더도 자동 전송 — `main.py:81-82`)
  - [ ] `RENDER_TOKEN=<길고 랜덤>`:
    ```bash
    python3 -c "import secrets; print(secrets.token_urlsafe(48))"
    ```
- [ ] 위 3개 중 하나라도 빠지면 backend 컨테이너가 **기동하다 crash**(`main.py:41-46`). crash = 버그 아니라 방어가 작동한 것. 로그 보고 빠진 값 채워라. 게이트를 우회하려 하지 마라.

#### A-4. 앱 자체 보안 — 파일럿에서 확인만 (기본 ON)

- [ ] **Rate limit 켜짐**: `.env`에 `RATE_LIMIT_ENABLED=False`가 **없는지** 확인(기본 True — `config.py:48`). 로그인 IP 20/5분, 이메일 5회 실패/15분, 가입 5/시간 자동 적용(`config.py:49-54`).
- [ ] **업로드 쿼터**: 인증 유저 20건/일, 미인증 3건/일(`config.py:58-60`). Anthropic 청구를 막는 **재정 방어선**. 파일럿에선 더 낮춰도 됨 → `.env`에 `UPLOAD_USER_LIMIT=5`.
- [ ] **멀티테넌시 격리**: 유저는 자기 잡만 본다(코드 강제). 파일럿에서 계정 2개로 교차 접근 안 되는지 1회 수동 확인.
- [ ] **이메일 인증(Resend)**: 현재 테스트모드, `EMAIL_FROM=onboarding@resend.dev`(`config.py:72`) — 본인 메일함 테스트용. 파일럿이 소수/지인이면 이대로 OK. 외부 공개 시 도메인 DKIM 검증 후 `EMAIL_FROM` 교체(배포 매뉴얼 다른 섹션).
- [ ] **관리자 계정 비밀번호**를 강하게. admin 이메일 = `dbstpgns789@gmail.com`.

#### A-5. 컨테이너 / 이미지

- [ ] **베이스 이미지 핀 고정**: `backend/Dockerfile:3` = `mcr.microsoft.com/playwright/python:v1.44.0-jammy`(arm64 지원 — 나중 Oracle Ampere 이사 대비). 재현성엔 좋으나 오래되면 Chromium 취약점 누적 → 아래 상시 체크로 갱신 판단.
- [ ] **root 실행 수용**: Playwright 공식 이미지는 컨테이너 안에서 root로 돈다. 파일럿에선 수용하되, `docker.sock`을 컨테이너에 마운트 안 한다(우리 compose는 안 함 — 유지).
- [ ] **backend에 `ports:` 절대 추가 금지**: `Dockerfile:21`이 `--forwarded-allow-ips *`로 뜬다(Caddy→web→backend 체인의 실 IP 신뢰용, 내부망이라 안전). 만약 backend에 호스트 포트를 열면 아무나 X-Forwarded-For를 위조해 **rate limit IP 카운터를 우회**할 수 있다. backend·web은 `expose`만 유지(외부 노출은 Caddy 80/443뿐).

#### A-6. 데이터 보호 / 백업

- [ ] ⚠️ **STORAGE_DIR 볼륨 함정(위험대장 C3)**: 현재 `docker-compose.yml:13-14`는 `/data`만 마운트하고 `STORAGE_DIR` 기본값은 컨테이너 내부 `backend/var/blobstore`(`config.py:35`). **이대로 배포하면 재배포/재생성 한 번에 카드PNG·export·유저 업로드 자산이 증발.** 배포 전 반드시:
  - [ ] compose backend `environment`에 `STORAGE_DIR=/data/blobstore` 추가(`polyinsight-data` 볼륨 아래)
  - [ ] `docker compose down && docker compose up -d` 후 자산이 살아남는지 1회 실증(위험대장 H5의 E2E)
- [ ] **소실 시 실제 피해 범위**: 카드PNG·export는 덱 구조가 DB에 있어 **재렌더로 복구 가능**(LLM 재호출 아님, Playwright만). 하지만 **유저 업로드 자산(`jobs/*/assets/`)은 재생성 불가** → 오직 `backup_assets`의 tar.gz로만 복구. 그래서 볼륨을 꼭 걸어야 한다.
- [ ] `/data` 볼륨 안 `polyinsight.db` + blobstore = 우리 전 재산. 백업 자동화(`backup_db.py` cron 등록)는 배포 섹션 참조. 스크립트가 **자체 integrity_check + 행 수 대조**로 사후검증하고 실패본은 `.unverified`로 격리한다(`backup_db.py:63-72`) — 조용한 손상 백업 방지.
- [ ] **백업 파일은 평문**: `backup_db.py`가 만드는 `.db`·`assets_*.tar.gz`는 암호화 안 됨. DB엔 **유저 이메일·argon2 비밀번호 해시·세션 해시**가 들어있다. VM 안 `backups/`(`git` 제외됨 — `.gitignore:93`)에 두는 건 OK지만, **VM 밖으로 복사할 땐 암호화**:
  ```bash
  gpg -c backups/polyinsight_20260713_030000.db   # 암호 물어봄 → .gpg 생성
  ```
- [ ] **복원은 리허설이 있다**: `backup_db.py` 상단 docstring의 7단계(uvicorn 정지→기존 DB rename→스냅샷 복사→wal/shm 삭제→기동→로그인 확인→assets tar 풀기). ⚠️ **DB 스냅샷과 assets tar를 같은 시점 쌍으로 복원**(어긋나면 dangling storage_key — `backup_db.py:13-15`).

---

### B. 상시 (운영 중 주기적으로)

#### 매주
- [ ] fail2ban 차단 현황: `sudo fail2ban-client status sshd`(차단 IP 폭증=정상, 무차별 대입은 원래 온다).
- [ ] **Anthropic 사용량/청구 확인**(console.anthropic.com) — 급증 = 키 유출 or 쿼터 우회 신호. 유일한 진짜 변동비라 여기가 조기경보. 덱 1개당 실비이므로 "예상 덱 수 × 단가"에서 벗어나면 즉시 C 섹션.
- [ ] `run.log`에서 로그인 실패·rate limit 히트 훑기(`main.py:28` FileHandler가 레포 루트 `run.log`에 씀).

#### 매월
- [ ] **OS 자동 보안패치**(1회 설정 후 자동):
  ```bash
  sudo apt install -y unattended-upgrades
  sudo dpkg-reconfigure -plow unattended-upgrades   # Yes
  ```
- [ ] **Playwright/베이스 이미지 갱신 검토**: `mcr.microsoft.com/playwright/python` 최신 안정 태그 확인 → `Dockerfile:3` 올리고 `docker compose build backend` → 덱 렌더가 여전히 되는지 1회 확인 후 배포. (Chromium 취약점이 여기로 들어온다.)
- [ ] **파이썬 의존성 스캔**:
  ```bash
  pip install pip-audit
  pip-audit -r backend/requirements.txt
  ```
- [ ] `.env` 밖-VM 백업 사본이 최신인지 확인(키 교체했으면 사본도 갱신).

---

### C. 시크릿 유출 시 대응 (터지면 뭐)

유출 의심되면 즉시 폐기·교체가 원칙(청구·계정 탈취가 훨씬 비쌈).

| 유출/의심 대상 | 즉시 할 일 | 발급처 |
|---|---|---|
| `ANTHROPIC_API_KEY`(청구 급증·노출) | 콘솔에서 해당 키 revoke → 새 키 → `.env` 교체 → `docker compose up -d backend` | console.anthropic.com |
| `RESEND_API_KEY` | Resend에서 키 삭제·재발급 → `.env` 교체 → backend 재기동 | resend.com |
| `RENDER_TOKEN` | A-3 명령으로 새 랜덤 → `.env` 교체 → backend 재기동 | 자체 생성 |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console에서 시크릿 재설정 → `.env` 교체 | Google Cloud Console |
| `.env` 통째 유출 | 위 **전부** 교체 + SSH 키쌍 교체. 기존 세션 무효화가 필요하면 DB의 sessions 테이블 정리 후 backend 재기동(세션은 DB 해시라 재시작만으론 안 죽음) | — |
| `.env`가 git에 커밋됨 | **값 교체가 먼저**(히스토리 삭제만으론 늦음 — 커밋된 순간 유출로 간주). 그 다음 히스토리 제거 | — |
| SSH 침해 의심(모르는 로그인) | NSG에서 22 임시 차단 → `sudo last` / `/var/log/auth.log` 확인 → SSH 키쌍 교체 → 필요시 VM 스냅샷 후 재생성 | Azure Portal |

- [ ] 대응 후: 서비스 정상 기동 확인(3 컨테이너 `docker compose ps`) + 로그인 1회 테스트 + Anthropic 청구 모니터링 강화.

---

### D. 절대 하지 마 (Never)

- [ ] **NSG에 3000/8000 인바운드 열지 마.** 외부 노출은 Caddy(80/443)뿐. web·backend를 직접 열면 우회·rate limit IP 위조. (80·443은 Caddy 앞문이라 열어 둔다 — 여긴 정상.)
- [ ] **backend/web에 compose `ports:` 추가하지 마.** `--forwarded-allow-ips *` 때문에 rate limit IP 우회 가능(A-5).
- [ ] **`.env`를 git에 커밋하지 마.** `git add -f`로 `.gitignore` 뚫지 마.
- [ ] **SSH 22를 0.0.0.0/0으로 열지 마.** 내 IP만.
- [ ] **SSH 비밀번호·root 로그인 켜지 마.**
- [ ] **호스트에 별도 nginx/certbot로 HTTPS 붙이지 마.** TLS 종단은 Caddy 컨테이너가 전담(Let's Encrypt 자동). 이중 종단은 구멍.
- [ ] **`COOKIE_SECURE=False`로 프로덕션 돌리지 마.** prod 게이트가 crash로 막지만, 게이트를 끄려 하지 마.
- [ ] **`ALLOWED_ORIGINS`/`PUBLIC_BASE_URL`을 http로만 두고 공개 배포하지 마.** 게이트가 안 켜져 secure 쿠키 없이 뜬다(A-3 함정).
- [ ] **`RATE_LIMIT_ENABLED=False`로 배포하지 마.** 재정 DoS·무차별 대입 방어선.
- [ ] **`docker.sock`을 컨테이너에 마운트하지 마.** 컨테이너 탈출 = 호스트 장악.
- [ ] **STORAGE_DIR 볼륨 안 걸고 배포하지 마**(C3). 유저 자산 소실.
- [ ] **백업 평문 파일을 VM 밖으로 암호화 없이 내보내지 마.** DB에 이메일·비번 해시 있음.
- [ ] **시크릿을 로그·스크린샷·메신저에 붙여넣지 마.** 박사님 전달 시에도 항목만.

---

**참조 파일(운영자용)**: `docker-compose.yml:13-16,27-28`(볼륨·expose·C3), `backend/main.py:33-46`(prod 게이트)·`81-82`(HSTS), `backend/core/config.py:35`(STORAGE_DIR)·`40-41`(COOKIE_SECURE·RENDER_TOKEN)·`48`(rate limit)·`58-60`(업로드 쿼터), `backend/Dockerfile:3`(베이스 핀)·`21`(forwarded-allow-ips), `backend/scripts/backup_db.py:13-15,63-72`(복원 리허설·사후검증), `.gitignore:15-17,93`(.env·backups 제외), `docs/superpowers/plans/2026-07-09-candidates-risk-register-and-roadmap.md`(위험대장 C3·H5·H1).

## 5. 비용

> 세 줄 요약: **인프라는 고정비(월 약 $30~35, Azure VM+디스크) — 예측 가능·저렴.** 진짜 무서운 건 **LLM 토큰(Opus 4.8)** — 덱 1개당 약 $0.5~1.2의 변동비이고, 박사님이 많이 만들수록 인프라비를 추월한다. $100 학생 크레딧은 VM 항상켜짐이면 약 3개월에 바닥나므로, **크레딧 소진 전에 Oracle ARM 무료로 이사**하는 게 이 다리 호스트의 존재 이유다.

---

### 1) Azure VM 월 비용 — 파일럿 사이즈와 러너웨이

backend 컨테이너는 **Playwright/Chromium(카드 렌더)**을 띄운다(`backend/Dockerfile:1-3`, playwright 공식 이미지). Chromium은 렌더 순간 300~700MB를 먹고, web(Next.js) 200~400MB + backend(FastAPI) 150MB가 상시 붙는다. 그래서 **RAM이 사이즈 선택의 병목**이다.

| VM 사이즈 | vCPU/RAM | 리눅스 PAYG(약) | 파일럿 적합성 |
|---|---|---|---|
| B1ms | 1 / 2GB | 약 $15/월 | ❌ Chromium 렌더 중 OOM 위험. 쓰지 말 것 |
| **B2s** | 2 / 4GB | **약 $30/월** | ⚠️ 최소 사양. 됨. 단 동시 렌더 몰리면 스왑/OOM → `MAX_CONCURRENT_JOBS`(현재 5, `config.py:36`)를 2~3으로 낮춰 방어 |
| B2ms | 2 / 8GB | 약 $60/월 | ✅ 여유. 크레딧이 버티면 안전빵 |

여기에 **OS 디스크(관리 디스크)** 약 $2~10/월(30GB StandardSSD ≈ 약 $2.4)이 더 붙는다. 앞문이 Caddy라 **공용 IP + 인바운드 80/443**을 쓴다(`docker-compose.yml:37-51`). 공용 IP는 소액(기본 SKU면 사실상 크레딧 커버 범위)이고 **Azure cloudapp 호스트네임·Let's Encrypt 인증서는 무료**라 앞문 비용은 0에 가깝다. 아웃바운드도 월 약 100GB까지 무료라 대역폭도 사실상 0이다.

**→ 파일럿 총 인프라비 ≈ 약 $30~35/월 (B2s + 디스크).**

**러너웨이 계산 (★중요):**
- $100 학생 크레딧, 유효기간 12개월.
- B2s **항상켜짐** ≈ 약 $33/월 → **$100은 약 3개월에 소진.** 12개월 전체를 못 버틴다.
- 이 호스트는 "다리"다. 3개월 안에 Oracle ARM 무료로 이사(5절)하거나, 안 쓸 때 **중지-할당해제**해서 시간당 과금을 멈춘다:
```bash
az vm deallocate --resource-group <RG> --name <VM>   # 시간당 과금 정지(디스크비는 계속)
az vm start      --resource-group <RG> --name <VM>   # 재개
```
- ⚠️ 할당해제하면 VM이 꺼져 **Caddy 앞문·시연 URL이 죽는다.** 파일럿 시연 링크를 상시 열어둬야 하면 항상켜짐이 강제되고, 그럼 3개월 시계가 돈다. (공용 IP 리소스에 DNS 라벨이 붙어 있어 호스트네임 자체는 유지되지만, VM이 꺼지면 응답이 없다.)

- [ ] 배포 후 첫 주: Azure Portal → 해당 VM → **Cost analysis**에서 하루치 실비를 보고 위 추정과 맞는지 대조
- [ ] B2s(4GB)면 `MAX_CONCURRENT_JOBS`를 2~3으로 낮췄는지 확인(`config.py:36`, `.env`로 override). OOM = 렌더 실패 = Chromium 좀비 프로세스

---

### 2) ★LLM 토큰 = 유일한 진짜 변동비

덱 저작은 `LLM_MODEL_AUTHOR = claude-opus-4-8`가 한다(`config.py:15`). **Opus 4.8 가격 = 입력 $5 / 출력 $25 (100만 토큰당).** config가 thinking 파라미터를 생략 → Opus 4.8은 thinking **off**로 돌아 추론 토큰 과금이 없다(`config.py:11-13` 주석·llm_client가 sampling 파라미터 자동 생략). Fable 5(thinking always-on, $10/$50)를 안 쓰는 이유가 이거다.

**덱 1개당 대략 얼마:**
- 입력 = 논문 추출 텍스트 + **few-shot 레퍼런스 덱 HTML 2개**(`AUTHOR_FEWSHOT_N=2`, `config.py:29`) + 프롬프트. few-shot 덱 HTML이 입력의 큰 덩어리다 ≈ 약 40,000~70,000 토큰 → 약 $0.2~0.35
- 출력 = 렌더 가능한 HTML 덱(`AUTHOR_MAX_TOKENS=32000` 천장, `config.py:17`. 실제 15,000~25,000) → 약 $0.4~0.6
- **합계 ≈ 덱 1개당 약 $0.5~1.2** (논문 크기에 좌우, "약"으로만)

**박사님이 N개 만들면:**
| 덱 수 | 대략 LLM 비용 |
|---|---|
| 10개 | 약 $8 |
| 100개 | 약 $80 |
| 500개 | 약 $400 |

**→ 손익분기: 월 약 40~45개 이상 만들면 LLM 비용이 인프라비($33)를 넘는다.** 파일럿에서 "몇 개 뽑았나"가 곧 비용이다. (편집=`claude-sonnet-4-6` $3/$15, `config.py:20` / 저지=`claude-sonnet-5`, `config.py:24`는 블랙박스 평가 전용이라 파일럿 일상 경로엔 거의 안 뜸 — 무시 가능.)

- [ ] 파일럿 시작 시 Anthropic 콘솔 Usage에서 "덱 1개 실호출" 1건을 찍어 **실제 입력/출력 토큰**을 확인하고 위 추정을 우리 논문 크기로 보정

---

### 3) 비용 폭탄 조건 — 우리 방어와 남은 구멍

| 폭탄 조건 | 코드 방어(있음) | 남은 구멍(감시 필요) |
|---|---|---|
| **재시도 폭주** | 스트리밍 1회 호출(`llm_client._stream_final`). truncation은 `LLMTruncationError` 발생 후 그대로 던짐(자동 재시도 없음) | 잡 레벨 자동 재시도 없음(수동 재요청뿐) → 사실상 방어됨 |
| **재시작 시 잡 되살아남** | `recover_stale_jobs`(`main.py:54`)가 재시작마다 PENDING/RUNNING을 **몰살**(ERROR 회수, 재실행 안 함) → 크래시 루프여도 토큰 재소모 안 함 | 단일 프로세스 전제. 워커 분리(L2) 후엔 이 전제가 깨지니 재검토 |
| **얇은/쓰레기 논문** | `_ABORT_WORD_FLOOR=80`(`pipeline.py:29,147`) — 80단어 미만은 저작 전 조기 차단. S1도 `_MIN_WORD_COUNT=100`(`s1_extractor.py:212`)으로 degraded 표면화 → Opus 호출 자체를 막음 | — |
| **거대 논문(입력 토큰 폭증)** | 출력은 `AUTHOR_MAX_TOKENS=32000` 천장 | ⚠️ **입력 토큰 상한 가드가 없다.** Opus 4.8은 1M 컨텍스트라 100페이지 논문도 에러 안 나고 그냥 비싸진다 → 덱 1개가 $2~5로 튈 수 있음. 파일럿에선 "긴 논문은 조심" 수동 운영으로 커버 |
| **악용(공개 URL로 누구나 Opus 호출)** | 이메일 인증 게이트 + 업로드 쿼터: 미인증 `UPLOAD_UNVERIFIED_LIMIT=3`/일, 인증 `UPLOAD_USER_LIMIT=20`/일, 가입 `SIGNUP_IP_LIMIT=5`/시간(`config.py:53-60`), rate limit | ⚠️ 인증 유저 1명이 하루 20개 = 약 $10~24/일까지 합법적으로 가능. 계정 여럿이면 배수. **파일럿은 아는 사람만(초대 위주), Anthropic 콘솔 월 한도(4절)로 하드 상한** |

- [ ] 파일럿 URL을 트위터/오픈웹에 뿌리지 말 것 — 공개 = 잠재 토큰 폭탄. 박사님·연구실 인원만
- [ ] "이상하게 긴 논문"이 올라오면 raw 로그에서 입력 토큰을 먼저 확인

---

### 4) 지출 상한 거는 법 (양쪽 다 걸어라 — 인프라는 Azure, 토큰은 Anthropic)

**Anthropic 콘솔 한도 (★토큰 폭탄 하드 상한 — 유일한 자동-차단):**
- `console.anthropic.com` → **Settings → Limits** → **Monthly spend limit**을 예: **$50/월**로 설정. 초과하면 API가 실제로 429/거부 → 악용·거대논문 폭탄을 물리적으로 막는다.
- **Usage** 페이지에서 일자별 토큰·비용 확인(어느 날 튀었는지).
- ⚠️ 한도에 걸리면 덱 생성이 실패한다(사용자에겐 렌더 실패로 보임). 한도는 "폭탄 방지선"이지 "정상 상한"이 아님 — 정상 사용량보다 넉넉히 잡되 폭주는 막을 수준으로.
- [ ] 배포 전: Anthropic 월 지출 한도 설정 완료 (이게 유일한 자동-차단 방어선)

**Azure 예산 알림 (인프라비 감시 — 알림만, 자동 차단 아님):**
- Portal: **Cost Management + Billing → Budgets → Add** → 월 예산 예: **$35** → 임계 50%/80%/100%에서 이메일 알림.
- 또는 CLI:
```bash
az consumption budget create \
  --budget-name polyinsight-pilot \
  --amount 35 --time-grain Monthly \
  --category Cost \
  --start-date 2026-08-01 --end-date 2027-07-31
```
- 학생 크레딧은 소진되면 리소스가 멈추는 게 기본 동작이라 그 자체가 하드 상한 역할.
- [ ] Azure 예산 $35 알림 설정 완료

---

### 5) 크레딧 소진 시 → Oracle ARM 무료로 이사

이 Azure VM은 다리다. 크레딧이 바닥나면(또는 러너웨이 계산상 임박하면) **컴퓨트를 Oracle Cloud Always Free ARM(Ampere A1)로 옮긴다.**

- **트리거:** Azure 예산 알림 80% 도달, 또는 잔여 크레딧으로 남은 개월 < 1.
- **왜 컴퓨트는 마찰이 적나:** `backend/Dockerfile:1-3`이 playwright 공식 이미지(arm64/Ampere 지원 명시)라 **ARM에서 그대로 뜬다.** backend·web·SQLite·볼륨은 그대로 이식된다.
- **⚠️ 앞문/도메인은 Oracle에서 '열린 결정'(그대로 이식 안 됨):** 지금 앞문은 **Caddy + Azure `cloudapp.azure.com` 무료 호스트네임**이고 이 호스트네임은 **Azure 전용**이다. Oracle엔 동급 무료 DNS 호스트네임이 없다. 그래서 Oracle에선 앞문/공개 주소를 다시 정해야 한다 — 옵션: ⓐ 도메인 구매 + Caddy(Let's Encrypt), ⓑ Cloudflare named 터널 + 도메인, ⓒ DuckDNS 같은 무료 동적 DNS + Caddy. 셋 다 `SITE_ADDRESS`(또는 앞문 서비스)만 바꾸면 되지만 **"같은 compose가 Oracle에서 앞문까지 그대로 뜬다"고 가정하지 말 것.** 공개 주소가 바뀌면 `.env`의 `PUBLIC_BASE_URL`·`ALLOWED_ORIGINS`·`SITE_ADDRESS`(+ OAuth 콜백·인증메일 링크)도 함께 갱신.
- **비용:** Oracle Always Free ARM = **컴퓨트 월 $0** (최대 4 OCPU/24GB까지 무료 — 4GB Azure보다 넉넉해 Chromium OOM 걱정도 줄어든다). 드는 건 인프라비가 아니라 **이사 노동(몇 시간)·데이터 이전·새 앞문 셋업**뿐(도메인을 사면 그 비용만 추가).

**★이사 전 반드시 C3 위험 먼저 해소 (안 고치면 이사 때 자산 통째로 소실):**
현재 `STORAGE_DIR` 기본값 = `backend/var/blobstore`(`config.py:35`, **이미지/레포 안쪽**). compose는 `/data` 볼륨만 마운트한다(`docker-compose.yml:13-14`). 즉 컨테이너 재생성·이사 시 카드PNG·export·유저자산이 증발한다(위험대장 C3, `docs/superpowers/plans/2026-07-09-candidates-risk-register-and-roadmap.md:27`).
- [ ] compose backend에 `STORAGE_DIR=/data/blobstore` 추가하고 그 경로가 `polyinsight-data` 볼륨 아래에 오게 한다. `.env.example`·런북 반영.
- [ ] compose down/up 후 자산이 그대로 남는지 실제로 확인(H5: prod 검증엔 이 sanity 체크가 아직 없음)

**이사 시 챙길 데이터(★백업 커버리지 정확히 알기):**
`backend/scripts/backup_db.py`가 뜨는 건 두 개다:
1. **DB** — `polyinsight.db`(VACUUM INTO, 사후 integrity 검증). `DATABASE_URL=sqlite:////data/polyinsight.db`(`docker-compose.yml:12`).
2. **자산 tar** — `assets_*.tar.gz`. ⚠️ **`jobs/*/assets/`(유저 업로드)만 담는다.** `cards/`·`exports/`는 "TTL 재생성 가능"이라 **의도적으로 제외**(`backup_db.py:82-84`).
- 즉 카드PNG·export는 백업에 없다 — 이사 후 **재렌더로 복원**되는 파생물이다. 원본 논문 자산(유저 업로드)만 tar로 보존된다.
- [ ] DB 스냅샷과 assets tar를 **같은 시점 쌍**으로 이전(어긋나면 storage_key 댕글링, `backup_db.py:15`)
- [ ] 이사 리허설: Oracle ARM에 compose 한 번 띄워 렌더(Chromium)까지 도는지 확인 후 실이전

**이사 후 잊지 말 것(prod-config 게이트가 startup에서 죽인다, `main.py:33-46`):** HTTPS 오리진 감지 시 `COOKIE_SECURE=True`·`PUBLIC_BASE_URL`(새 공개 도메인)·`RENDER_TOKEN`이 없으면 backend가 startup crash한다. 신 호스트 `.env`에 이 3개 + 앞문 서비스용 `SITE_ADDRESS`(또는 Oracle에서 고른 앞문 옵션) 반드시 세팅.

---

### 6) 월 비용 감시 체크리스트

매월(또는 격주) 1회:
- [ ] **Anthropic Usage** — 이번 달 토큰 비용, 일자별 스파이크 여부. 특정 날짜가 튀었으면 그날 raw 로그에서 거대 논문/악용 흔적 확인
- [ ] Anthropic 월 지출 한도가 여전히 설정돼 있는가(콘솔에서 초기화 안 됐는지)
- [ ] 이번 달 만든 덱 수 × 약 $0.8 ≈ Anthropic 실비와 얼추 맞나? 크게 벌어지면 재시도/거대입력 누수 의심
- [ ] **Azure Cost analysis** — 이번 달 인프라 실비가 약 $33 근처인가? 튀었으면 디스크·불필요 리소스 확인
- [ ] **남은 학생 크레딧 ÷ 월 지출 = 남은 개월.** 1개월 미만이면 Oracle 이사 착수
- [ ] `MAX_CONCURRENT_JOBS`와 VM RAM이 여전히 안전 범위인가(OOM 로그 유무)

**관련 파일:** `backend/core/config.py`(모델·쿼터·`AUTHOR_MAX_TOKENS`·`MAX_CONCURRENT_JOBS`·`STORAGE_DIR`), `backend/agents/deck/pipeline.py`(thin-input 조기차단 `_ABORT_WORD_FLOOR`·잡 세마포어), `backend/core/llm_client.py`(스트리밍 1회·truncation 무재시도), `backend/scripts/backup_db.py`(이사용 백업·자산 tar 커버리지), `backend/main.py`(`recover_stale_jobs`·prod-config 게이트), `docker-compose.yml`(볼륨·앞문 caddy·DATABASE_URL), `deploy/Caddyfile`(앞문 리버스 프록시).

## 6. 배포 (첫 배포 · 재배포 · 롤백)

> 대상 독자: DevOps 경험이 적은 1인 운영자. 아래 명령을 **위에서 아래로 순서대로** 그대로 따라 하면 된다. VM 안에서 실행하는 셸은 모두 `bash`(Ubuntu 기본)다.

이 스택의 핵심 그림 (실측):

- Azure VM 리눅스 1대 위에서 `docker compose`가 컨테이너 3개를 돌린다: `backend`(FastAPI + Playwright/Chromium), `web`(Next.js), `caddy`(앞문 리버스 프록시 + 자동 HTTPS). (`docker-compose.yml:5-51`)
- 외부에서 접속하는 주소는 **Azure 무료 호스트네임 `https://polyinsight.japaneast.cloudapp.azure.com`** 하나뿐이다. Caddy가 인바운드 80·443을 받아 `web:3000`으로 프록시하고, `backend`·`web`은 `expose`만 하고 포트를 호스트로 공개하지 않는다(backend `docker-compose.yml:17`, web `30`). VM 방화벽(NSG)은 **22·80·443**을 연다.
- 데이터는 두 곳에 산다: **DB**(`/data/polyinsight.db`, SQLite)와 **파일 저장소**(카드 PNG·export·유저 업로드 자산, `STORAGE_DIR`). 이 둘이 **재배포 후에도 살아남게** 만드는 게 이 문서에서 제일 중요한 부분이다.

---

### 0. 배포 전 체크리스트 (첫 배포·재배포 공통)

- [ ] `ANTHROPIC_API_KEY`(Opus 저작용) 유효한 키 확보 — 없으면 덱 생성이 전부 실패한다(유일한 진짜 변동비, `config.py:7,15` `LLM_MODEL_AUTHOR=claude-opus-4-8`).
- [ ] `SITE_ADDRESS=polyinsight.japaneast.cloudapp.azure.com` 확정(Azure 공용 IP의 DNS 이름 레이블 = `polyinsight`, 리전 Japan East). Caddy가 이 도메인으로 자동 HTTPS를 켠다. NSG **80·443** 개방 필수.
- [ ] `RENDER_TOKEN` 강한 랜덤값 생성해 둠(`openssl rand -hex 32`).
- [ ] `.env` 준비 완료 + 아래 §2의 **프로덕션 필수 항목**이 채워짐.
- [ ] **STORAGE_DIR 볼륨 픽스**(§1-5)가 `docker-compose.yml`에 반영됨 — 안 하면 재배포 한 번에 유저 자산 전량 증발(위험대장 C3, `docker-compose.yml:13-14`가 `/data`만 마운트 + `config.py:35` 기본값이 레포 안 `backend/var/blobstore`).
- [ ] **백업 볼륨 마운트**(§1-5)가 반영됨 — 안 하면 백업 파일이 컨테이너와 함께 사라진다(`backup_db.py:106` 기본 `dest=backups/`는 컨테이너 안 임시경로).
- [ ] 기존 데이터가 있는 서버라면 §4(이주) 먼저 수행할 것을 인지.
- [ ] 진행 중인 덱 생성 잡이 없는 시간대에 배포(재배포 시 진행 잡이 죽는다 — §5).

---

### 1. 첫 배포 스텝 바이 스텝

#### 1-1. Azure VM 생성

Azure Portal → **Virtual machines → Create → Azure virtual machine**.

| 항목 | 값 | 이유 |
|---|---|---|
| Region | **Korea Central (한국 중부)** | 국내 접속 지연 최소 |
| Image | **Ubuntu Server 22.04 LTS** | Docker 표준, compose가 리눅스 가정 |
| Size | **Standard_B2s** (2 vCPU / 4 GiB) 권장 | Chromium 렌더(`backend/Dockerfile:3` Playwright 이미지) + Next 빌드가 메모리를 먹는다. 1GB(B1s)는 빌드·렌더 중 OOM 위험 |
| Authentication | **SSH public key** | 비밀번호 로그인보다 안전 |
| OS disk | Standard SSD **30 GiB** | DB·자산·도커 이미지 여유 |
| Public inbound ports | **SSH (22) + HTTP (80) + HTTPS (443)** | 앞문이 Caddy라 80/443을 직접 받고 Let's Encrypt가 80으로 도메인을 검증한다. 3000/8000은 열지 않는다 |

> 비용 감각: B2급 종량제는 약 월 $30~35 수준이라 $100 Azure for Students 크레딧(12개월)을 **약 3개월**에 소진한다. 이 VM은 "다리 호스트"다 — 크레딧 소진 전 Oracle ARM 무료 호스트로 **컴퓨트를** 이사하는 게 계획(backend Playwright 이미지가 arm64 지원 `backend/Dockerfile:2`. 단 앞문/도메인은 Azure 전용이라 Oracle에선 재결정 — §5-5). 크레딧을 아끼려 VM을 꺼두면(deallocate) Caddy 앞문·공개 링크가 끊기므로 **켜둔 채로** 크레딧 잔량을 Portal에서 주기적으로 확인한다.

생성 후 SSH 접속:

```bash
ssh -i <내려받은키>.pem azureuser@<VM_공인IP>
```

#### 1-2. Docker + Compose 설치 (VM 안에서)

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER          # sudo 없이 docker (재로그인 후 적용)

# 재접속 후 확인
docker version
docker compose version                 # v2 (플러그인). 'docker-compose' 하이픈 아님
```

메모리 4GB 이하면 빌드 OOM 방지용 스왑 2GB 추가:

```bash
sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab   # 재부팅 후에도 유지
```

#### 1-3. 코드 가져오기

```bash
git clone <레포_URL> polyinsight
cd polyinsight
```

#### 1-4. `.env` 준비

레포에 `.env.example`이 있다. 복사해 실제 값을 채운다. **`.env`는 절대 git에 커밋하지 않는다**(시크릿 포함).

```bash
cp .env.example .env
nano .env                # 아래 §2 표대로 채움
openssl rand -hex 32     # 출력값을 .env의 RENDER_TOKEN= 에 붙여넣기
```

#### 1-5. ★ STORAGE_DIR + 백업 볼륨 픽스 (첫 배포 전 반드시)

**현재 `docker-compose.yml`은 `backend`에 `/data` 볼륨만 걸고 `STORAGE_DIR`을 지정하지 않는다**(`docker-compose.yml:10-14`). 그러면 `STORAGE_DIR`이 기본값 `backend/var/blobstore`(컨테이너 내부, 볼륨 아님, `config.py:35`)로 떨어져서 **컨테이너를 재생성(`up --build`, `down/up`)할 때마다 카드 PNG·export·유저 업로드 자산이 전부 사라진다**(위험대장 C3). DB(`/data/polyinsight.db`)만 살아남고 자산은 증발해 화면이 깨진다.

또한 **백업 파일 저장 경로도 같은 함정에 빠진다**: `backup_db.py`의 기본 `dest`는 `backups/`(cwd 상대, `backup_db.py:106`)라 컨테이너 안에서 돌리면 임시경로에 쌓여 컨테이너와 함께 사라진다.

`docker-compose.yml`의 `backend` 서비스를 아래처럼 고친다:

```yaml
  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env
    environment:
      - WEB_BASE_URL=http://web:3000
      - DATABASE_URL=sqlite:////data/polyinsight.db
      - STORAGE_DIR=/data/blobstore      # ★ 추가: 자산을 영속 볼륨(/data) 안에 저장
    volumes:
      - polyinsight-data:/data           # DB + 자산 (이미 있음)
      - ./backups:/data/backups          # ★ 추가: 백업을 호스트 파일로 (오프사이트 복사·볼륨손실 대비)
    expose:
      - "8000"
    restart: unless-stopped
```

확인 포인트:
- `STORAGE_DIR`은 **반드시 `/data` 아래**(같은 볼륨)여야 한다. `/data/polyinsight.db`(DB)와 `/data/blobstore`(자산)가 한 볼륨에 있어야 백업·복원 시점이 어긋나지 않는다.
- 백업은 `./backups`(호스트 디렉토리)로 뺀다 — VM 파일시스템에 남아 `scp`로 다른 곳에 복사할 수 있고, 도커 볼륨이 통째로 날아가도 살아남는다.

> 이 픽스는 배포 아티팩트(compose)의 문제라 코드 테스트로는 안 잡힌다. 배포 후 §7 스모크의 "재배포 후 자산 잔존" 검증으로만 증명된다(위험대장 H5).

#### 1-6. 앞문(Caddy) + 공개 호스트네임 세팅

앞문은 **Caddy 컨테이너**(`caddy:2`, `docker-compose.yml:37-51`)다. 별도 토큰 발급은 없다. 준비할 것은 두 가지뿐:

1. **Azure 공용 IP에 DNS 이름 레이블 지정** — Azure Portal → VM → 개요의 공용 IP 클릭 → **Configuration** → "DNS 이름 레이블"에 `polyinsight` 입력·저장. 그러면 `polyinsight.japaneast.cloudapp.azure.com`이 이 공용 IP(20.210.112.15)로 해석된다. **도메인 구매 0원.**
2. **`.env`에 `SITE_ADDRESS`** — `SITE_ADDRESS=polyinsight.japaneast.cloudapp.azure.com`(스킴 없는 맨호스트). Caddy가 이 값으로 Let's Encrypt HTTPS를 자동 발급하고 `web:3000`으로 프록시한다(`deploy/Caddyfile` = `{$SITE_ADDRESS} { reverse_proxy web:3000 }`).

인증서 발급 조건: **NSG 80·443 개방 + 호스트네임이 공용 IP로 해석**돼야 Let's Encrypt HTTP-01 챌린지가 통과한다. 발급된 인증서는 `caddy-data` 볼륨(`docker-compose.yml:46`)에 영속되어 재시작마다 재발급(레이트리밋)되지 않는다.

#### 1-7. 빌드 & 기동

```bash
docker compose up -d --build
```

- 첫 빌드는 backend가 Playwright/Chromium 이미지(`mcr.microsoft.com/playwright/python:v1.44.0-jammy`)를 받고 `playwright install chromium`을 돌려 오래 걸린다(수 분, `backend/Dockerfile:3,10-11`).
- `web`은 `BACKEND_ORIGIN=http://backend:8000`을 **빌드 시점 build arg로 굽는다**(`docker-compose.yml:26`) — 런타임 env로는 못 바꾼다. 이 값이 바뀌면 반드시 `--build`.

#### 1-8. 헬스 확인

```bash
docker compose ps                            # 세 서비스 모두 Up, restarting 아님
docker compose logs backend --tail=50
docker compose logs web --tail=30
docker compose logs caddy --tail=20          # "certificate obtained successfully" 나오면 HTTPS 발급 성공
```

backend 로그에서 확인할 것:

- [ ] `_validate_prod_config` 통과 — startup crash 없이 `Application startup complete`(uvicorn)가 뜸(아래 함정 참고).
- [ ] `RuntimeError` 없음.
- [ ] (참고) 재시작 고아 잡이 있으면 `stale job N건 ERROR로 회수` 로그가 뜬다(`main.py:56`) — 첫 배포엔 정상적으로 없음.

**★ startup crash 함정** (`main.py:33-46`): `_validate_prod_config`는 `ALLOWED_ORIGINS`나 `PUBLIC_BASE_URL`에서 `https://`를 감지하면(=프로덕션 판단) `COOKIE_SECURE`·`PUBLIC_BASE_URL`·`RENDER_TOKEN` 셋을 강제한다. 하나라도 비면 backend가 **기동 직후 죽는다**(fail-closed, `restart: unless-stopped`라 계속 재시작 루프). 로그에 아래가 보이면 `.env`를 고치고 `docker compose up -d backend`:

- `HTTPS 배포인데 COOKIE_SECURE=False` → `.env`에 `COOKIE_SECURE=True`
- `HTTPS 배포인데 PUBLIC_BASE_URL 미설정` → `.env`에 공개 도메인(`https://polyinsight.japaneast.cloudapp.azure.com`)
- `HTTPS 배포인데 RENDER_TOKEN 미설정` → `openssl rand -hex 32` 값

마지막으로 브라우저에서 **공개 도메인(`https://polyinsight.japaneast.cloudapp.azure.com`)**을 열어 자물쇠(유효 인증서)와 랜딩 페이지가 뜨는지 확인한다. 인증서가 아직이면 `docker compose logs caddy`에서 ACME 진행/에러를 본다.

---

### 2. `.env` 필수 항목 표

| 키 | 설명 | 프로덕션 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Opus 덱 저작용 키. 없으면 덱 생성 전부 실패(유일한 실 변동비) | **필수** |
| `COOKIE_SECURE` | 세션 쿠키 Secure. 앞문(Caddy)=HTTPS라 `True` 안 하면 startup crash | **필수(=True)** |
| `PUBLIC_BASE_URL` | 사용자 접속 공개 도메인 `https://polyinsight.japaneast.cloudapp.azure.com`. 인증메일 링크·OAuth 콜백 베이스. 비우면 내부호스트로 링크 깨지고 crash (`config.py:76-78`) | **필수** |
| `RENDER_TOKEN` | 내부 렌더(Playwright) 우회 토큰(`openssl rand -hex 32`). 최상위 시크릿 — 로그 금지 | **필수** |
| `SITE_ADDRESS` | Caddy 앞문이 자동 HTTPS를 켤 **공개 FQDN**(스킴 없이) `polyinsight.japaneast.cloudapp.azure.com`. caddy 서비스가 이걸로 인증서 발급(`docker-compose.yml:40`). 시크릿 아님 | **필수(caddy)** |
| `ALLOWED_ORIGINS` | CORS 허용 오리진(쉼표구분). 여기에 `https://`가 들어가야 prod 게이트가 켜짐(`main.py:39`) | **필수** |
| `RESEND_API_KEY` | Resend 이메일 키. 비우면 인증메일 no-op(가입은 되나 메일 안 감). 현재 테스트모드 | 권장 |
| `EMAIL_FROM` | 발신 주소. DKIM 도메인 검증 전엔 `onboarding@resend.dev`로 본인함 테스트만 (`config.py:72`) | 조건부 |
| `DATABASE_URL` | compose가 `sqlite:////data/polyinsight.db`로 덮어씀(`docker-compose.yml:12`). `.env` 값 무시 | (compose 처리) |
| `STORAGE_DIR` | 자산 루트. compose environment에서 `/data/blobstore` 지정(§1-5) | **필수(§1-5)** |
| `PEXELS_API_KEY` / `UNSPLASH_ACCESS_KEY` | 스톡 이미지 검색(선택). 비우면 검색만 빈결과, 업로드는 정상 | 선택 |

> `ALLOWED_ORIGINS`(또는 `PUBLIC_BASE_URL`)에 반드시 `https://` 도메인을 넣어야 prod 보안 게이트(HSTS·Secure 쿠키)가 켜진다(`main.py:37-39,81`). `http://`만 있으면 코드가 "로컬 개발"로 오판해 보안 헤더가 빠진다. Google OAuth를 켜면 `OAUTH_REDIRECT_BASE`도 같은 `https://polyinsight.japaneast.cloudapp.azure.com`으로 맞춘다(현재 OAuth는 dormant).

---

### 3. 첫 배포냐, 기존 데이터 이주냐 (분기)

- **완전 신규 서버**(DB·자산 없음): §4 건너뛴다. §1대로 하면 끝.
- **기존 데이터가 있는 서버**(예전 버전이 BLOB을 DB 안에 저장하던 시절 데이터): §4 이주를 **반드시 먼저**. 안 하면 옛 `card_images`·`exports`·`deck_assets` BLOB이 새 코드에서 조용히 안 보인다(위험대장 H1).

판단이 애매하면: `polyinsight.db`가 이미 존재하고 잡 데이터가 있으면 "기존 데이터 있음"으로 본다.

---

### 4. 기존 데이터 이주 (migrate_blobs_to_disk) — 기존 데이터 있을 때만

예전 스키마는 이미지·export·자산 바이너리를 SQLite 안(BLOB)에 넣었다. 새 코드는 파일 저장소(`STORAGE_DIR`)에서 읽는다(`migrate_blobs_to_disk.py:1-5`). 그 사이를 메우는 일회성 이주다. **순서 엄수**:

```bash
# 1) 서버 정지 (이주 중 쓰기 방지)
docker compose down

# 2) 백업 먼저 (되돌릴 안전망)
#    ★ --dest /data/backups (영속 경로), --min-bytes 1 (신규/소형 DB 가드 완화)
docker compose run --rm backend python -m backend.scripts.backup_db --dest /data/backups --min-bytes 1

# 3) 이주 실행 (멱등 — 이미 옮긴 행 skip, 전 행 옮기면 BLOB 컬럼 DROP)
docker compose run --rm backend python -m backend.scripts.migrate_blobs_to_disk
#    출력: "이주 완료: N건 파일로 이동, BLOB 컬럼 정리됨."

# 4) 새 코드로 기동
docker compose up -d --build
```

> 이주는 멱등하다(`migrate_blobs_to_disk.py:3,32`) — 중간에 끊겨도 다시 돌리면 남은 것만 옮긴다. 대상: `card_images`·`exports`·`deck_assets`. 이주 후 자산은 `STORAGE_DIR/jobs/{job_id}/...` 아래 파일로 존재한다(`migrate_blobs_to_disk.py:20-22`).

---

### 5. 재배포 / 업데이트 (코드 갱신)

```bash
cd ~/polyinsight
git pull
docker compose up -d --build     # 바뀐 서비스만 재빌드·재생성, 볼륨은 유지
```

**무엇이 보존되나**: `polyinsight-data:/data` 볼륨은 `down`을 하지 않는 한(또는 해도 `-v` 없이는) 유지되므로 DB·자산이 보존된다 — **단 §1-5 STORAGE_DIR 픽스가 되어 있어야 한다**. 안 되어 있으면 자산 증발.

> ⚠️ `web`을 재빌드할 때 `BACKEND_ORIGIN` 등 build arg가 바뀌면 반드시 `--build`로 다시 구워야 반영된다(런타임 env로는 안 바뀜, `docker-compose.yml:26`).

**★ 재배포 주의 — 진행 중인 잡이 죽는다** (`main.py:54`, `db.py:453`): startup의 `recover_stale_jobs`는 단일 프로세스 전제라, backend가 재시작되면 그 시점 `PENDING`/`RUNNING`(대기·생성 중) 잡을 전부 `ERROR`로 회수한다. 즉 **누군가 덱을 만드는 중에 재배포하면 그 덱이 실패로 죽는다**(위험대장 C2/H6). 그래서:

- [ ] 재배포는 **진행 잡이 없는 한산한 시간**에.
- [ ] 데모·시연 중이면 상대의 덱 생성이 끝난 뒤 배포.
- [ ] 활성 잡 확인은 로그보다 DB가 확실:
  ```bash
  docker compose run --rm backend python -c "import sqlite3; print(sqlite3.connect('/data/polyinsight.db').execute(\"SELECT status, COUNT(*) FROM jobs GROUP BY status\").fetchall())"
  ```
  `RUNNING`/`PENDING`이 0이면 안전.

---

### 6. 롤백

업데이트 후 문제가 터지면 **이전 커밋 + 이전 데이터 백업을 짝으로** 되돌린다. 코드만 되돌리고 DB를 안 맞추면 스키마가 어긋날 수 있다.

```bash
# 1) 정지
docker compose down

# 2) 코드를 직전 정상 커밋으로
git log --oneline -5            # 되돌릴 커밋 해시 확인
git checkout <이전_정상_커밋>

# 3) DB를 그 시점 백업으로 복원 (backup_db.py 헤더 복원 6단계, backup_db.py:6-15)
#    - /data 안 polyinsight.db → polyinsight.db.broken 으로 rename
#    - backups/polyinsight_YYYYMMDD_HHMMSS.db 를 polyinsight.db 로 복사
#    - 잔존 polyinsight.db-wal / -shm 삭제
#    - (이주 이후라면) 같은 시점 assets_YYYYMMDD_HHMMSS.tar.gz 를 STORAGE_DIR 에 풀기:
#      tar xzf assets_....tar.gz -C /data/blobstore

# 4) 이전 코드로 재빌드·기동
docker compose up -d --build

# 5) 로그인 되는지 확인
```

> ⚠️ DB 스냅샷과 자산 tar는 **같은 시점 쌍**으로 복원한다. DB의 `storage_key`와 실제 파일이 어긋나면 카드가 깨진 채(dangling) 뜬다(`backup_db.py:15`).
>
> **카드 PNG는 assets 백업에 없다**: `backup_assets`는 영속 자산(`jobs/*/assets/`)만 담고 재생성 가능한 `cards/`·`exports/`는 제외한다(`backup_db.py:83-84`). 볼륨이 통째로 날아가 카드가 사라지면, 덱 구조는 DB에 있으니 재렌더로 되살릴 수 있다(LLM 비용 없음, Playwright만).

---

### 7. 배포 후 스모크 테스트 (사람이 브라우저로 직접)

공개 도메인(`https://polyinsight.japaneast.cloudapp.azure.com`)에서 실제 유저 흐름을 처음부터 끝까지:

- [ ] **가입**: 회원가입 → 동의 체크 → 대시보드 도착(자동 로그인). 인증메일 쓰면 메일함(스팸함 포함) 확인.
- [ ] **논문 1건 업로드**: `/deck/new`에서 PDF + 아트디렉션 브리핑 입력 → 잡 생성됨.
- [ ] **덱 생성**: RENDER 진행이 카드별로 채워짐(N/M) → 카드 완성(최대 7장, `config.py:28`). (여기서 Opus 실비 1회 발생 — 사전 허락 규칙)
- [ ] **export**: 내보내기 모달 → PNG/zip 다운로드 성공.
- [ ] **★ 재배포 후 자산 잔존(제일 중요)**: `docker compose down && docker compose up -d` 후 방금 만든 덱을 다시 열어 **카드 이미지가 그대로 보이면** STORAGE_DIR 볼륨 픽스(§1-5)가 제대로 됐다는 증거다. 깨지면 §1-5로 돌아가 `STORAGE_DIR=/data/blobstore` + 볼륨 마운트 재확인.

하나라도 실패하면 `docker compose logs backend --tail=100`으로 원인(대개 `.env` 키 누락 또는 STORAGE_DIR)을 본다.

---

### 8. 배포 후 반드시 이어서 할 일

- **백업 자동화 등록**: `backup_db.py`는 만들어져 있으나 cron 미등록 상태다(`backup_db.py:20-21` 주석의 예시는 로컬 `.venv` 기준 — 컨테이너 배포엔 아래로 대체). 매일 03:00 스냅샷(DB + `assets_*.tar.gz`):
  ```bash
  crontab -e
  # 아래 한 줄 추가 (경로는 실제 레포 위치로)
  0 3 * * * cd /home/azureuser/polyinsight && docker compose run --rm backend python -m backend.scripts.backup_db --dest /data/backups --min-bytes 1 >> /home/azureuser/backup.log 2>&1
  ```
  - `--dest /data/backups` 필수 — §1-5에서 `./backups`를 호스트로 마운트했으므로 백업이 VM 파일로 남는다.
  - `--min-bytes 1` — 기본 가드가 1MB라(`backup_db.py:43,107`) 파일럿 초기 소형 DB에서 백업이 조용히 실패(exit 1)하는 걸 막는다. DB가 커지면 원래 가드로 올려도 된다.
  - 주기적으로 `scp azureuser@<VM>:~/polyinsight/backups/ ...`로 **VM 밖에도** 복사해 두면 VM 자체 소실에 대비된다. → 상세는 백업/복구 섹션.
- **크레딧 소진 전 Oracle ARM 이사(컴퓨트 한정)**: backend·web·SQLite는 arm64에서 그대로 뜬다(backend Playwright 이미지 arm64 지원, `backend/Dockerfile:2`). 이사 = 새 호스트에 §1-2~1-5·1-7·1-8 반복 + `/data` 볼륨·`backups/` 복사. ⚠️ **단 §1-6 앞문은 Azure cloudapp 호스트네임 전용** — Oracle에선 앞문/도메인을 재결정해야 한다(도메인 구매+Caddy / Cloudflare named 터널+도메인 / DuckDNS+Caddy, §5-5). → 마이그레이션 섹션.

## 7. 모니터링 & 유지보수 (일상 운영)

> 대상: DevOps에 익숙하지 않은 1인 운영자.
> 원칙: **매일 30초 → 주 5분 → 월 15분.** 아래 명령은 모두 리포지토리 루트(`docker-compose.yml`이 있는 폴더)에서 실행합니다. 서버 접속은 `ssh <사용자>@<VM_IP>` 후 그 폴더로 이동(`cd polyinsight`).
> 비용 숫자는 전부 "약(대략)"입니다.

---

### 0. 먼저 외울 4가지 (우리 스택의 진실)

1. **전용 헬스 엔드포인트가 없다.** `/api/health` 같은 건 없습니다. 등록된 API는 auth·jobs·projects·export·images·deck 뿐입니다(`backend/main.py:97-102`). "살아있나?"는 **컨테이너 상태 + 실제 접속**으로 판단하고, 내부 핑은 FastAPI 자동 문서 페이지 `/docs`(200이면 앱 프로세스 살아있음)를 씁니다.
2. **백엔드는 외부에 노출되지 않는다.** `docker-compose.yml`에서 backend는 `expose: 8000`만 있고 포트 매핑(`ports:`)이 없습니다(`docker-compose.yml:17-18`). 외부로 나가는 문은 **Caddy(80/443) → web:3000** 한 곳뿐(`docker-compose.yml:37-51`). 그래서 백엔드 점검은 `docker compose exec`로 컨테이너 안에 들어가서 합니다.
3. **재시작하면 진행 중이던 덱 생성은 전부 죽는다.** `recover_stale_jobs`(`backend/core/db.py:509`, `main.py:54`)가 서버 시작 시 PENDING/RUNNING 잡을 **전량 ERROR로 회수**합니다(단일 프로세스 전제). 즉 **덱을 만드는 중(수 분, Opus 호출 진행 중)에는 `docker compose restart`/재배포를 하지 마세요.** 사용자에게 실패가 뜨고 그 덱의 Opus 비용은 날아갑니다.
4. **파일 로그(`run.log`)에는 날짜가 없다.** 로그 포맷이 시간(`%H:%M:%S`)만 찍습니다(`backend/main.py:24`). 언제 난 에러인지 알려면 `docker compose logs -t`(도커 타임스탬프)를 함께 보세요.

---

### 1. "살아있나?" 확인 (매일 30초)

체크리스트 — 위에서 아래로:

- [ ] **컨테이너 3개 다 Up인가**
  ```bash
  docker compose ps
  ```
  `backend`, `web`, `caddy` 세 서비스가 모두 `Up`(또는 `running`)이어야 정상. `Restarting`이 반복되면 크래시 루프 → §5-B.
- [ ] **실제 사이트가 열리나** (진짜 최종 확인)
  브라우저로 공개 URL(`https://polyinsight.japaneast.cloudapp.azure.com`) 접속 → 로그인 화면이 뜨면 OK. 이게 되면 Caddy·web·(로그인까지 되면 backend까지) 살아있는 것.
- [ ] **백엔드가 응답하나** (사이트가 안 열릴 때만)
  ```bash
  docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/docs').status)"
  ```
  `200`이면 백엔드 자체는 정상 → 문제는 web 또는 앞문(Caddy).
- [ ] **앞문(Caddy)이 인증서를 받았나** (사이트가 안 열리거나 자물쇠 경고일 때만)
  ```bash
  docker compose logs --tail=30 caddy
  ```
  `certificate obtained successfully` / `serving initial configuration` 줄이 보이면 정상. `ACME`/`obtaining certificate` 에러가 반복되면 §5-A(NSG 80/443·호스트네임 해석 확인).

> 팁: `~/.bashrc`에 별칭 추가 →
> `alias pi-check='docker compose ps && docker compose logs --tail=5 caddy'`

---

### 2. 로그 보기 (무엇이 어디에)

| 위치 | 내용 | 보는 법 |
|---|---|---|
| Docker 표준 로그(stdout) | uvicorn 요청/에러, Next.js, Caddy 인증서·프록시 상태 | `docker compose logs` |
| `backend` 컨테이너 내부 `/app/run.log` | 백엔드 파이프라인·LLM·렌더 상세(`backend/main.py:28`이 파일로깅, WORKDIR=/app) | `docker compose exec backend tail -f /app/run.log` |

⚠️ **`run.log`는 컨테이너 내부 파일 → 컨테이너를 새로 만들면(재배포) 사라진다.** 장애 원인을 남기려면 재배포 전에 꺼내세요:
```bash
docker compose cp backend:/app/run.log ./run.log.$(date +%F)
```

**실시간 따라보기 (도커 타임스탬프 켜서 날짜 확보):**
```bash
docker compose logs -f -t              # 전체 3개 서비스
docker compose logs -f -t backend      # 백엔드만 (파이프라인/LLM/렌더)
```

**무엇을 찾나 (에러 종류별):**

- [ ] **LLM(Opus) 에러** — `ANTHROPIC`, `LLMTruncation`, `overloaded`, `rate_limit`, `401`, `529`. 덱 저작 실패의 대부분. `401`=API 키 문제, `overloaded`/`529`=Anthropic 혼잡(자동 재시도). 이건 곧 **새는 돈**이니 우선 확인.
  ```bash
  docker compose logs backend | grep -iE "anthropic|llm|truncat|overload|rate.?limit"
  ```
- [ ] **렌더(Playwright/Chromium) 실패** — `playwright`, `Timeout`, `Target closed`, `chromium`. 카드 PNG가 안 나오는 증상(`PLAYWRIGHT_TIMEOUT_MS` 기본 15초).
  ```bash
  docker compose logs backend | grep -iE "playwright|chromium|timeout|target closed"
  ```
- [ ] **stale job 몰살 흔적** — 재시작 후 `stale job N건 ERROR로 회수 (서버 재시작 고아)` 줄(`backend/main.py:56`). N이 크면 진행 중 작업을 밟고 재시작했다는 뜻.
- [ ] **startup 크래시** — backend가 계속 재시작하면 로그 맨 위 `RuntimeError`. `_validate_prod_config`(`backend/main.py:33-46`)가 HTTPS 배포에서 `COOKIE_SECURE`/`PUBLIC_BASE_URL`/`RENDER_TOKEN` 누락 시 **기동 자체를 거부**합니다. → §5-B.

---

### 3. 외부 업타임 감시 (설정 1회, 이후 자동)

내가 로그를 24시간 볼 수 없으므로, 밖에서 주기적으로 찔러보고 죽으면 **이메일/문자 알림**을 받게 해둡니다.

- [ ] 무료 모니터(예: UptimeRobot) 가입.
- [ ] **HTTP(S) 모니터** 추가 → URL = 공개 URL `https://polyinsight.japaneast.cloudapp.azure.com`(로그인 페이지), 5분 간격.
  - 헬스 엔드포인트가 없으니 로그인/랜딩 페이지의 **HTTP 200**을 살아있음 신호로 씁니다(§0-1).
  - 가능하면 "키워드 모니터"로 페이지 고정 문구(예: "PolyInsight")까지 검사 → 앞문은 살아도 앱이 에러 페이지를 주는 경우까지 잡힘.
  - TLS 만료 감시도 켜두면(UptimeRobot의 SSL 모니터) Let's Encrypt 자동 갱신이 실패한 경우를 조기에 잡습니다.
- [ ] 알림 수신처(이메일/휴대폰) 등록. **다운 + 복구** 둘 다 알림 켜기.

> 이 감시는 "Caddy+web 살아있나"까지만 봅니다. 백엔드 파이프라인/LLM 실패는 로그(§2)와 사용자 신고로 파악.

---

### 4. 디스크 관리 (가장 흔한 조용한 죽음)

데이터는 `/data` 볼륨(`polyinsight-data`)에 쌓입니다: **SQLite DB**(`/data/polyinsight.db` + `-wal`/`-shm`). 디스크가 꽉 차면 **DB 쓰기 실패 → 로그인·저장 전부 500**.

- [ ] **호스트 디스크 여유**
  ```bash
  df -h /
  ```
  80% 넘으면 정리, 90% 넘으면 위험.
- [ ] **볼륨 안에서 뭐가 큰지**
  ```bash
  docker compose exec backend sh -c "du -sh /data/* 2>/dev/null | sort -h | tail"
  ```

**자동으로 줄어드는 것 (건드릴 필요 없음):**
- TTL 청소기 `cleanup_expired_blobs`가 **30분마다** 돌며(`backend/main.py:64-69`, `db.py:660`) 만료된 card_images·exports·deck_assets(`EXPORT_TTL_HOURS=24`, `config.py:32`)와 만료 세션·인증 토큰을 삭제.

**수동으로 줄여야 하는 것:**
- [ ] **Docker 찌꺼기 정리** — 재배포를 반복하면 옛 이미지가 수 GB 쌓입니다(Playwright 이미지가 약 2GB로 큼). 월 1회:
  ```bash
  docker image prune -f          # 태그 없는 옛 이미지
  docker builder prune -f        # 빌드 캐시
  ```
  ⚠️ `docker system prune`에 `--volumes`를 **절대 붙이지 마세요.** `polyinsight-data` 볼륨(=DB)이 지워집니다.

> ⚠️ **알려진 위험 C3** (위험대장): 현재 `docker-compose.yml`은 `/data`만 마운트하고(`docker-compose.yml:13-14`) `STORAGE_DIR` 기본값은 컨테이너 안 `backend/var/blobstore`(`config.py:35`)라 **재배포 시 카드PNG·export·유저 업로드 자산이 증발**합니다. 배포 안전 조치(compose backend에 `STORAGE_DIR=/data/blobstore` + `.env`)가 적용됐는지 반드시 확인. 적용 전이면 자산은 임시로 취급하고, 재배포 전 자산 백업(백업 섹션 참조) 필수.

---

### 5. "앱이 죽었다" 런북 (증상 → 진단 → 조치)

항상 `docker compose ps`로 어느 컨테이너가 문제인지 특정한 뒤 아래로.

#### A. 앞문(Caddy)/HTTPS 문제 — 사이트만 안 열림 또는 인증서 경고, 컨테이너는 Up
- 진단: `docker compose exec backend python -c "import urllib.request;print(urllib.request.urlopen('http://localhost:8000/docs').status)"` → 200(=백엔드 정상). 그러면 문제는 web 또는 Caddy. `docker compose logs --tail=50 caddy`에서 `certificate obtained successfully`(정상) 또는 `ACME`/`obtaining certificate` 에러를 본다.
- 조치:
  ```bash
  docker compose restart caddy
  ```
  그래도 인증서 에러면: ① **NSG 80·443이 열려 있나**(닫히면 Let's Encrypt HTTP-01 챌린지 실패) ② **호스트네임이 공용 IP로 해석되나**(`nslookup polyinsight.japaneast.cloudapp.azure.com` → 20.210.112.15) ③ `.env`의 `SITE_ADDRESS`가 맞나 → 고친 뒤 `docker compose up -d caddy`. 발급 성공 인증서는 `caddy-data` 볼륨에 남아 재시작에도 유지된다.

#### B. 컨테이너 죽음 / 재시작 반복 — `Restarting` 또는 `Exit`
- 진단: `docker compose logs --tail=80 backend`(또는 web) 맨 위 예외를 읽는다.
  - `RuntimeError: HTTPS 배포인데 COOKIE_SECURE=False ...` 류 → `_validate_prod_config` 게이트(`main.py:33-46`). `.env`에 `COOKIE_SECURE=True`, `PUBLIC_BASE_URL=<공개 도메인>`, `RENDER_TOKEN=<임의 긴 문자열>` 채우기.
  - 그 외 예외 → 최근 코드/`.env` 변경 되돌리기.
- 조치: `.env` 고친 뒤 `docker compose up -d`.

#### C. 디스크 풀 — 로그인·저장이 전부 500, `df -h`가 90%+
- 조치: §4 Docker 정리 → 부족하면 옛 백업/`run.log`/옛 이미지 삭제. 근본 해결은 VM 디스크 증설(Azure 포털 → VM → 디스크). **`--volumes` prune 금지.**

#### D. 메모리 풀 / Chromium OOM — 렌더 중 backend가 갑자기 죽거나 `Target closed`
- 배경: 렌더가 backend 프로세스 안에서 Chromium을 띄웁니다(단일 프로세스). 논문 여러 개가 동시에 렌더되면 메모리가 튐.
- 진단:
  ```bash
  docker stats --no-stream              # backend MEM% 확인
  sudo dmesg | grep -i "killed process" # OOM 킬 흔적 (호스트, sudo 필요할 수 있음)
  ```
- 조치(즉시): `docker compose restart backend`. (진행 중 잡은 §0-3대로 회수됨.)
- 조치(재발): 동시 처리량 낮추기 → `.env`에 `MAX_CONCURRENT_JOBS`를 기본 5(`config.py:36`)보다 낮게(예: 2). 그래도 잦으면 VM RAM 증설. Playwright/Chromium이 무거우니 **RAM 최소 약 2GB, 약 4GB 권장.**

#### E. DB 락 — 저장이 가끔 실패, 로그에 `database is locked`
- 배경: SQLite는 동시 쓰기 1개만 허용(WAL). 백업 중이거나 순간 경합에서 드물게 발생.
- 조치: 대개 일시적 → 잠시 후 재시도되면 정상. 반복되면 그 시각에 무거운 배치(백업·대량 렌더)가 겹쳤는지 로그 확인. `docker compose restart backend`로 해소.

---

### 6. 정기 유지보수 캘린더

**매일 (30초)**
- [ ] `docker compose ps` — 3개 Up
- [ ] 공개 URL 눈으로 한 번 접속

**매주 (5분)**
- [ ] `docker compose logs --since 168h backend | grep -iE "error|exception|truncat|overload|timeout"` — 한 주간 에러 훑기 (도커 `--since`는 "7d"를 못 읽으니 시간 단위 `168h` 사용)
- [ ] `df -h /` — 80% 미만 유지
- [ ] 백업 폴더에 최신 스냅샷이 실제로 쌓이는지 확인(백업 섹션)

**매월 (15분)**
- [ ] `docker image prune -f && docker builder prune -f`
- [ ] **백업 복원 리허설** — 백업본으로 실제 복구 1회 시험. 절차는 `backend/scripts/backup_db.py` 상단 docstring(복원 6~7단계). "백업이 있다" ≠ "복원된다".
- [ ] Azure for Students **크레딧 잔액**(포털 → Cost Management). 약 $100/12개월. 소진 임박하면 Oracle ARM 무료 이전(같은 compose) 준비.
- [ ] **Anthropic Opus 사용량**(console.anthropic.com → Usage) 확인 — 유일한 진짜 변동비. 예상보다 급증하면 로그에서 재시도 폭주/남용 계정 의심.
- [ ] `docker compose pull caddy && docker compose up -d caddy` — 앞문(Caddy) 이미지 업데이트.

**분기 / 필요 시**
- [ ] 앱 코드 배포: 반드시 **정지 → DB·자산 백업 → migrate → 재배포** 순서(위험대장 H1). 재배포 전 §0-3대로 **진행 중 덱이 없을 때** 수행.

---

### 7. 우리 스택 특유의 함정 (외우기)

- **재시작 = 진행 중 잡 몰살.** `recover_stale_jobs`(`db.py:509`)가 재시작마다 PENDING/RUNNING을 ERROR로 회수(단일 프로세스 전제). **덱 생성 중 재시작/재배포 금지.** 워커 분리(로드맵 L2) 전까지 유효.
- **단일 프로세스·단일 호스트.** web=워커=한 프로세스로 코드가 가정. 인스턴스를 2개로 늘리면 잡 중복 픽업·세션 분열. 확장은 L2 이후.
- **Chromium이 메모리를 먹는다.** 렌더가 backend 안에서 돈다 → 동시성(`MAX_CONCURRENT_JOBS`, `config.py:36`)과 VM RAM이 안정성의 핵심 레버.
- **헬스 엔드포인트 없음.** 살아있음 판단 = `docker compose ps` + 실제 접속 + `/docs` 내부 핑(§0-1).
- **`run.log`는 비영속·날짜 없음.** 컨테이너 재생성 시 소멸, 시간만 찍힘(`main.py:24,28`). 원인 보존은 재배포 전 `docker compose cp`, 날짜는 `docker compose logs -t`.
- **진짜 변동비는 Opus 호출뿐.** 인프라(VM·앞문 Caddy)는 사실상 고정/무료. 로그에 LLM 에러가 잦다 = 곧 새는 돈.
- **백업 스크립트는 컨테이너를 모른다.** `backup_db.py`는 cwd 상대경로 전제인데 compose DB는 컨테이너 안 절대경로(`/data/polyinsight.db`, `docker-compose.yml:12`)이고 호스트엔 `.venv`가 없다 → 호스트에서 그냥 실행하면 DB를 못 찾음. 백업은 **컨테이너 안에서** 돌려야 함(백업 섹션 참조).
- **`--volumes` prune 절대 금지.** 그 한 번에 DB가 사라진다.

## 8. 백업 & 재해복구

목표는 딱 하나 — **"VM이 디스크째 사라져도 서비스를 다시 띄운다."** DevOps 경험이 없어도 복붙으로 따라 할 수 있게, 명령·체크리스트·"언제·무엇을·터지면 어떻게" 순으로 정리한다.

우리 스택에서 잃으면 못 되살리는 데이터는 딱 두 덩어리다.

1. **SQLite DB** (`/data/polyinsight.db`) — 회원·세션 + **저작된 덱(`authored_deck`, 영구 보존)**. 날아가면 계정과 유저 결과물이 통째로 사라진다.
2. **L1 영속 자산** (`STORAGE_DIR/jobs/<job_id>/assets/`) — 유저가 올린 이미지·`deck_assets` 바이너리. 덱 저작의 재료라 재생성 불가.

카드 PNG와 export ZIP은 24시간 TTL이라 언제든 재렌더로 다시 만든다 → **백업 대상 아님**. `.env`(비밀값)는 백업에 안 들어가니 **VM 밖에 따로 보관**(맨 아래 참고).

---

### ⚠️ 0단계 — 백업 켜기 전에 C3부터 고쳐라 (선행 필수)

현재 `docker-compose.yml`은 볼륨을 `/data` 하나만 마운트하고(13-14행), `STORAGE_DIR` 기본값은 컨테이너 안 `backend/var/blobstore`다(`config.py:35`). 즉 **유저 자산이 컨테이너 임시 레이어에 쌓인다 → 재배포(`docker compose up --build`) 한 번에 전량 증발**(위험대장 C3). 이 상태에선 자산 백업을 돌려도 "임시 폴더를 백업"하는 헛수고고, 진짜 위험은 그대로다.

백업 자동화 켜기 전에 반드시 아래를 먼저 반영한다(배포 안전 Phase 2와 동일).

- [ ] `docker-compose.yml` backend `environment:`에 `- STORAGE_DIR=/data/blobstore` 추가
- [ ] `.env` / `.env.example`에도 `STORAGE_DIR=/data/blobstore` 명시
- [ ] `docker compose up -d --build` 후 `docker compose exec backend ls /data/blobstore` 로 자산이 볼륨 안에 있는지 확인
- [ ] `docker compose down && docker compose up -d` 재기동 후에도 기존 덱/자산이 살아있는지 웹에서 육안 확인

> 왜 중요한가: `backup_assets()`는 `settings.STORAGE_DIR`를 그대로 tar로 묶는다(`backup_db.py:82,116`). STORAGE_DIR가 임시 폴더면 **백업이 임시 폴더를 뜬다.** 아래 절차는 전부 `STORAGE_DIR=/data/blobstore`(= DB와 같은 영속 볼륨)를 전제한다.

---

### 무엇을 백업하나

| 대상 | 위치(컨테이너 내부) | 도구 | 필수? | 이유 |
|---|---|---|---|---|
| SQLite DB | `/data/polyinsight.db` | `backup_db.py` `backup()` (`VACUUM INTO`) | ✅ | 회원·세션·**저작 덱(영구)** |
| L1 유저 자산 | `/data/blobstore/jobs/*/assets/` | `backup_db.py` `backup_assets()` (tar.gz) | ✅ | 덱 저작 재료, 재생성 불가 |
| 카드 PNG | `card_images` (24h TTL) | — | ❌ | 재렌더로 재생성 |
| export ZIP | `exports` (24h TTL) | — | ❌ | 재생성 |
| **`.env` (비밀값)** | 레포 루트 (볼륨 밖) | **수동·별도 보관** | ✅ | 백업에 안 들어감. 아래 "VM 통째로" 참고 |

`backend/scripts/backup_db.py`를 한 번 실행하면 위 두 대상을 **같은 타임스탬프**로 스냅샷한다(`__main__`이 `backup()` 후 `backup_assets()` 연달아 호출, `backup_db.py:113-116`).

- **DB**: `VACUUM INTO`로 조각모음된 단일 파일 → **사후 자가검증**(`PRAGMA integrity_check` + users/jobs 행 수 대조). 실패 시 `.unverified`로 rename해 보존하고 exit 1 (`backup_db.py:64-72`).
- **자산**: `assets_YYYYMMDD_HHMMSS.tar.gz`로 `jobs/*/assets`만 묶는다(재생성 가능한 cards/·exports/ 제외, `backup_db.py:82-100`).
- **보존**: `--keep N`(기본 7)개만 남기고 오래된 타임스탬프 스냅샷 삭제. 수동 네이밍 백업은 안 건드림.

> 초기 함정: 신규 DB가 1MB 미만이면 `min_bytes` 가드(엉뚱한 DB 백업 방지)에 걸려 abort한다(`backup_db.py:43,48`, 기본 `1_000_000`). 파일럿 초기엔 `--min-bytes 100000`처럼 낮춰 실행.

---

### 매일 자동 백업 걸기 (현재 미등록 — cron으로 등록)

핵심 두 가지: 백업은 **backend 컨테이너 안에서** 돌려야 하고(DB·자산이 거기 있음), 스냅샷은 **`/data/backups`(영속 볼륨 안)** 에 떨궈야 컨테이너를 갈아엎어도 산다.

호스트에 래퍼 하나 두고 cron이 부른다. `/home/azureuser/polyinsight/ops/backup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
cd /home/azureuser/polyinsight            # docker-compose.yml 있는 곳

# 1) 컨테이너 안에서 DB+자산 스냅샷 (검증·보존 7개 자동)
docker compose exec -T backend \
  python -m backend.scripts.backup_db --dest /data/backups

# 2) 볼륨 안 백업을 호스트 스테이징으로 꺼냄
STAGE=/home/azureuser/polyinsight-backups/staging
rm -rf "$STAGE" && mkdir -p "$STAGE"
docker compose cp backend:/data/backups/. "$STAGE"

# 3) 오프-VM(Azure Blob)로 밀기 — 아래 "오프-VM" 절 참고
az storage blob upload-batch \
  --connection-string "$AZURE_STORAGE_CONNECTION_STRING" \
  --destination backups --source "$STAGE" --overwrite

echo "$(date -Is) backup+offvm OK"
```

등록:

```bash
chmod +x /home/azureuser/polyinsight/ops/backup.sh
crontab -e
```

crontab 한 줄 (매일 새벽 3시, 연결 문자열 주입 + 로그):

```cron
0 3 * * * AZURE_STORAGE_CONNECTION_STRING="$(cat /home/azureuser/.az_conn)" /home/azureuser/polyinsight/ops/backup.sh >> /home/azureuser/polyinsight-backups/backup.log 2>&1
```

- [ ] `backup.sh` 실행 권한(`chmod +x`)
- [ ] 연결 문자열을 `/home/azureuser/.az_conn`에 저장하고 `chmod 600`
- [ ] `crontab -l`로 줄 등록 확인
- [ ] 다음날 `backup.log`에 `integrity=ok`와 `backup+offvm OK`가 찍혔는지 확인
- [ ] `docker compose exec backend ls -la /data/backups`로 스냅샷이 쌓이는지 확인

> `docker compose exec`는 backend가 떠 있어야 동작한다(compose `restart: unless-stopped`라 평소 떠 있음). 정지 중이면 `backup.log`에 에러가 남아 바로 티 난다.

---

### ★ 오프-VM 사본 (이게 없으면 재해복구는 무의미)

`/data/backups`는 VM의 같은 디스크·같은 도커 볼륨 안이다. **VM이 죽으면 백업도 같이 죽는다.** 반드시 VM 밖으로 민다. 호스트가 Azure VM이니 자연스러운 목적지는 **Azure Blob Storage**(Azure for Students 크레딧으로 커버, 백업 용량 수십 MB라 비용 **약 월 $1 미만**).

**최초 1회 준비 (Azure 포털이 제일 쉬움):**

1. 포털 → Storage accounts → Create. 리전 `Korea Central`, 이중화 `LRS`(제일 쌈), 이름은 전역 유일(예: `polyinsightbak`).
2. 만든 계정 → Containers → `backups` 컨테이너 생성.
3. 계정 → Access keys → **Connection string** 복사 → VM의 `/home/azureuser/.az_conn`에 붙여넣고 `chmod 600`.
4. VM에 az CLI 설치: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`

**보안 강화(선택):** 연결 문자열은 계정 전체 권한을 준다. VM이 털리면 스토리지도 털린다. 파일럿엔 수용 가능하지만, 나중에 **관리 ID(Managed Identity) + `Storage Blob Data Contributor` 롤**로 바꾸면 VM에 키를 안 둬도 된다(그 땐 `--connection-string` 대신 `--auth-mode login`).

**오프-VM 보존:** 볼륨 안은 7개(스크립트), 오프-VM은 더 길게. 포털에서 컨테이너에 **수명주기(Lifecycle) 규칙**을 걸어 30~40일 지난 blob 자동 삭제.

- [ ] Storage 계정·`backups` 컨테이너 생성
- [ ] 연결 문자열 `/home/azureuser/.az_conn`(chmod 600)에 저장
- [ ] az CLI 설치
- [ ] `backup.sh` 수동 1회 실행 후 포털에서 blob 올라갔는지 확인
- [ ] Lifecycle 규칙(예: 40일) 등록

> az CLI가 부담스러우면 rclone 원격을 `azureblob`으로 잡고 3단계를 `rclone sync "$STAGE" azureblob:backups`로 바꿔도 된다.

---

### 복원 드릴 — DB + 자산 (Docker)

**대원칙: DB 스냅샷과 자산 tar는 같은 실행에서 나온 짝(같은 타임스탬프)으로 복원**한다. 어긋나면 DB의 `storage_key`가 없는 파일을 가리키는 **dangling** 상태가 된다.

```bash
cd /home/azureuser/polyinsight

# 0. 복원할 짝 결정 (예: polyinsight_20260713_030001.db + assets_20260713_030001.tar.gz)

# 1. backend 정지
docker compose stop backend

# 2. 현재 DB를 broken으로 보존 (증거 남김, 볼륨 안)
docker compose run --rm -T backend sh -c 'mv /data/polyinsight.db /data/polyinsight.db.broken'

# 3. 백업 스냅샷을 현역 DB로 복사
docker compose run --rm -T backend sh -c \
  'cp /data/backups/polyinsight_20260713_030001.db /data/polyinsight.db'

# 4. 잔존 WAL/SHM 삭제 (안 지우면 옛 미커밋 트랜잭션이 되살아나 정합 깨짐)
docker compose run --rm -T backend sh -c 'rm -f /data/polyinsight.db-wal /data/polyinsight.db-shm'

# 5. 같은 시각 자산 tar를 STORAGE_DIR로 풀기 (tar 안 경로가 jobs/... 라 -C /data/blobstore)
docker compose run --rm -T backend sh -c \
  'tar xzf /data/backups/assets_20260713_030001.tar.gz -C /data/blobstore'

# 6. 기동
docker compose start backend
```

- [ ] `docker compose logs backend`에 startup crash 없음(prod-config 게이트 통과)
- [ ] 웹에서 로그인 성공
- [ ] 복원된 유저의 덱을 열어 카드가 보임(자산 dangling 없음)
- [ ] 문제없으면 `/data/polyinsight.db.broken` 삭제

> `docker compose run --rm backend sh -c '...'`는 CMD(uvicorn)를 덮어써 파일 작업만 하고 빠지는 안전한 방식. backend가 stop된 상태여도 같은 볼륨을 마운트하므로 조작 가능. backend 이미지는 Debian(jammy) 기반이라 `sh`·`cp`·`mv`·`tar`·`rm` 다 있다(`Dockerfile:3`).
>
> ⚠️ 복원 후 첫 기동 때 `recover_stale_jobs`가 백업 시점에 진행중이던 PENDING/RUNNING 잡을 전부 ERROR로 회수한다(`main.py:54`, `db.py:509`). 정상 동작이니 놀라지 말 것 — 유저가 그 덱만 다시 생성하면 된다.

---

### VM이 통째로 죽었을 때 (전체 재해복구)

VM 삭제·디스크 장애·실수로 `docker compose down -v`(볼륨까지 삭제) 등으로 호스트가 통째로 날아간 경우.

**먼저 반드시 알 것 — `.env`는 백업에 없다.** DB 백업에도 자산 tar에도 안 들어간다. 그런데 `.env`가 없으면 애초에 서비스가 안 뜬다:

- `main.py:_validate_prod_config`(33-46행)가 https 오리진 감지 시 `COOKIE_SECURE`·`PUBLIC_BASE_URL`·`RENDER_TOKEN` 없으면 **startup crash**(fail-closed).
- `SITE_ADDRESS` 없으면 Caddy가 자동 HTTPS를 못 켜 앞문(공개 URL)이 안 뜬다.
- `ANTHROPIC_API_KEY` 없으면 덱 저작 불가.

→ `.env`는 **비밀번호 매니저나 Azure Key Vault 등 VM 밖 안전한 곳에 따로 보관**하고, secret 로테이션 때마다 갱신한다. 이것 없으면 데이터 복원해도 못 띄운다.

복구 순서:

```bash
# 1. 새 Ubuntu VM 프로비저닝 → docker + docker compose 설치 + az CLI 설치

# 2. 레포 확보
git clone <레포 URL> polyinsight && cd polyinsight

# 3. .env 복원 (별도 안전보관에서) — 이게 없으면 startup crash
cp /secure-vault/polyinsight.env .env

# 4. Azure Blob에서 최신 스냅샷 내려받기
mkdir -p restore
az storage blob download-batch \
  --connection-string "$(cat /home/azureuser/.az_conn)" \
  -s backups -d ./restore

# 5. 빈 볼륨 만들고 스냅샷 주입 (짝 1개만 두고 실행 — 아래 주의)
docker volume create polyinsight-data
docker run --rm -v polyinsight-data:/data -v "$PWD/restore":/restore alpine sh -c '
  cp /restore/polyinsight_*.db /data/polyinsight.db &&
  mkdir -p /data/blobstore &&
  tar xzf /restore/assets_*.tar.gz -C /data/blobstore'

# 6. 기동 (compose가 STORAGE_DIR=/data/blobstore 넣도록 0단계 반영됐는지 확인)
docker compose up -d --build

# 7. 확인 — Caddy가 새 VM에서 Let's Encrypt 인증서를 다시 발급하는지
docker compose logs -f caddy      # "certificate obtained successfully"
```

- [ ] **공개 URL 복구**: 새 VM은 **새 공용 IP**를 받는다. 같은 리전(Japan East)에서 새 공용 IP에 DNS 이름 레이블 `polyinsight`를 재지정하면 **같은 호스트네임(`polyinsight.japaneast.cloudapp.azure.com`)이 복구**된다(구 IP 리소스는 먼저 삭제/해제해야 라벨 충돌 안 남). 라벨을 못 되살리면 새 호스트네임 → `.env`의 `SITE_ADDRESS`·`PUBLIC_BASE_URL`·`ALLOWED_ORIGINS`(+ OAuth 콜백·인증메일 링크) 갱신 후 재기동.
- [ ] NSG 80·443 개방 확인(신규 VM은 규칙을 다시 걸어야 인증서 발급됨).
- [ ] 로그인·덱 열기·새 덱 저작(Anthropic 키 살아있나) 각 1회 확인
- [ ] `restore/`에 스냅샷이 여러 개면 **DB와 assets를 같은 타임스탬프 짝**만 골라 복원(위 명령의 `*` 글롭은 짝이 1개일 때만 안전 — 여러 개면 파일명을 명시)

---

### 데이터 보존 / TTL (무엇이 언제 사라지나)

`_ttl_cleaner`가 **30분(1800초)마다** `cleanup_expired_blobs()`를 호출해 만료분을 자동 정리한다(`main.py:64-71`).

| 데이터 | 수명 | 백업 필요 | 근거 |
|---|---|---|---|
| 저작 덱 `authored_deck` | **영구** | ✅ (DB 백업) | `expires_at` 컬럼 없음 — 정리 대상 아님 |
| 유저 자산 `deck_assets` | **30일**(재편집 시 갱신) | ✅ (assets tar) | `db.py:454` `ttl_hours=24*30` |
| 카드 PNG `card_images` | 24시간 | ❌ | `db.py:554` 재렌더 재생성 |
| export ZIP `exports` | 24시간 | ❌ | `db.py:619` 재생성 |
| 세션·인증 토큰 | TTL | (DB에 딸려옴) | 만료분 자동 삭제 |

즉 24시간 지난 카드/export는 어차피 지워지니 백업해봐야 소용없고, **30일 자산 + 영구 덱**만 지키면 된다.

---

### 백업 검증 체크리스트 (정기)

"백업 파일이 있다"와 "그 백업이 실제로 복원된다"는 다른 문제다. 정기적으로 아래를 돌린다.

**매주(로그 확인):**
- [ ] `backup.log` 최근 줄에 `integrity=ok`와 `backup+offvm OK`
- [ ] `/data/backups`와 Azure Blob **양쪽**에 어제/오늘 스냅샷 존재
- [ ] `/data/backups`에 `.unverified` 파일 없음(있으면 백업 손상 — 즉시 조사)

**분기 1회(실제 복원 드릴):**
- [ ] 스크래치 볼륨(`polyinsight-restore-test`)에 최신 스냅샷 복원 → 임시 compose로 기동 → 로그인·덱 열기까지 성공 확인 후 스크래치 볼륨 삭제
- [ ] `.env` 사본이 최신인지(secret 로테이션 이후 갱신했나)
- [ ] Azure 크레딧 잔액·Lifecycle 규칙 살아있는지
- [ ] DB↔자산 짝 정합: 복원한 덱에서 카드 이미지가 dangling 없이 보이는지

## 9. 인프라 생애주기 & 관리

> 이 섹션 대상 = **DevOps 처음인 1인 운영자**. "지금 Azure에 뭐가 떠 있고, 어디서 보고, 언제·무엇을 바꾸고, 크레딧 떨어지면 어떻게 이사하나"를 순서대로. 화면(Azure Portal) 위주로 쓰고, 명령(SSH·docker)은 복붙 가능하게 붙인다.

### 0. 한눈에 — 지금 우리가 굴리는 것

```
[내 노트북]  ──ssh(22)──▶  [Azure VM (Ubuntu), 공용 IP 20.210.112.15]
                          └ docker compose 로 컨테이너 3개
                             ├ backend  (FastAPI + Playwright/Chromium)  ← 무거움(RAM 먹는 놈)
                             ├ web      (Next.js)
                             └ caddy (앞문)  ◀──inbound 80/443──  [Let's Encrypt HTTPS]  ◀──  사용자
                          └ docker 볼륨 polyinsight-data → /data (SQLite DB) · caddy-data(인증서)
```

핵심 사실 4가지 (이거만 외워도 절반):

- **앞문은 Caddy 리버스 프록시**다. caddy 컨테이너가 호스트 **80·443**을 열어(compose:41-43) Let's Encrypt로 HTTPS를 종단하고 `web:3000`으로 프록시한다. backend·web은 여전히 호스트 포트를 안 연다(`expose`만 — compose:17-18,30-31). → **NSG에 22·80·443**을 연다(80은 인증서 발급용). ⚠️ VM 공용 IP(20.210.112.15)가 직접 노출되고 Cloudflare 은닉·DDoS 방어는 없다.
- **데이터는 docker 볼륨 `polyinsight-data`(/data) 한 곳**에만 산다(compose:13-14,42-43). VM이 죽어도 이 볼륨만 살아있으면 DB는 산다. ⚠️ **단, 지금은 SQLite DB만 이 볼륨에 있고, 카드 PNG·export·유저 업로드 자산(STORAGE_DIR)은 볼륨 밖**(컨테이너 안 `backend/var/blobstore`, config.py:35). 컨테이너를 새로 만들면 이게 사라진다(위험 C3 — §5에서 반드시 조치).
- **진짜 돈 나가는 건 두 개뿐**: Azure VM(고정비, 크레딧 차감) + Anthropic **Opus** 토큰(덱 만들 때마다 변동비, config.py:15 `LLM_MODEL_AUTHOR`). 나머지(Caddy·Next·FastAPI, Let's Encrypt 인증서)는 약 $0.
- **Azure는 다리(bridge)다.** 학생 크레딧 다 쓰면 **컴퓨트를** Oracle ARM 무료로 이사한다(§6). backend 이미지가 arm64 지원(`mcr.microsoft.com/playwright/python`, Dockerfile:2-3)이라 그대로 뜬다. ⚠️ **단 앞문(Caddy + Azure cloudapp 호스트네임)은 Azure 전용** — Oracle엔 무료 DNS 호스트네임이 없어 앞문/도메인은 재결정(§5-5·§9-3). "compose가 앞문까지 그대로 뜬다"고 보지 말 것.

---

### 1. Azure 리소스 목록 — 뭐가 있고 어디서 보나

운영자가 알아야 할 리소스는 6개뿐이다. 전부 **하나의 리소스 그룹** 안에 넣어두면 관리·삭제가 쉽다.

| 리소스 | 이게 뭔가 | Portal 위치 | 왜 신경 쓰나 |
|---|---|---|---|
| **리소스 그룹** | 나머지 5개를 담는 폴더 | 검색창 → "리소스 그룹" | 이걸 삭제하면 안의 모든 게 한 번에 삭제됨. 실수 주의 |
| **가상 머신(VM)** | 우리 컴퓨터 1대 | "가상 머신" → 이름 클릭 | 켜짐/꺼짐·크기·비용의 원천 |
| **디스크(Disk)** | VM에 붙은 OS 저장소 | VM → 왼쪽 "디스크" | 꽉 차면 배포·렌더 실패. `df -h`로 감시(§4) |
| **네트워크 보안 그룹(NSG)** | 방화벽 규칙 | VM → "네트워킹" | **22·80·443이 열려 있어야 정상**(80/443=Caddy 앞문·인증서). 3000/8000 열려 있으면 닫아라 |
| **공용 IP** | 앞문·SSH 주소 (20.210.112.15) | VM 개요 화면 상단 | 이 주소로 ssh. 동시에 **앞문(80/443)이자 공개 도메인이 가리키는 IP** — DNS 이름 레이블 `polyinsight`가 여기 붙어 `polyinsight.japaneast.cloudapp.azure.com`으로 해석됨 |
| **예산(Budget)** | 크레딧 소진 경보 | 검색 → "비용 관리 + 청구" → "예산" | **가장 중요.** 안 걸면 조용히 크레딧 증발 |

체크리스트 — VM 만들고 나서 한 번에 확인:
- [ ] 리소스 그룹 이름을 적어 뒀다 (예: `rg-polyinsight`) → §7 기록장에.
- [ ] NSG 인바운드 규칙에 **22·80·443**이 있다(80/443=Caddy 앞문). 3000/8000/기타 열려 있으면 삭제.
- [ ] SSH(22)를 **내 IP에서만** 허용(NSG 규칙 source = `My IP`). 80·443은 전체 개방(Let's Encrypt·서비스용). 안 되면 최소한 키 인증만 쓰고 비밀번호 로그인 끈다.
- [ ] 공용 IP(20.210.112.15)와 DNS 이름 레이블(`polyinsight`)을 적어 뒀다.
- [ ] 예산 경보를 걸었다(아래).

#### 비용·예산 — 크레딧 감시 (이게 §6 이사 트리거)

- 학생 크레딧 = 약 $100 / 12개월. **하지만 VM을 24시간 켜두면 12개월 못 간다.**
  - backend의 Playwright/Chromium이 큰 HTML을 렌더하려면 RAM이 넉넉해야 함(약 4GB↑ 권장). 이 정도 크기(예: B2s급, vCPU 2·RAM 4GB)를 상시로 켜두면 **월 약 $30~40** → 크레딧이 **약 2~3개월**이면 바닥.
  - 즉 "$100 = 12개월"은 **가끔 켜는** 파일럿 기준. 상시 운영이면 크레딧은 몇 달치다. 이 현실을 박사님께 미리 공유.
- **예산 경보 거는 법**: Portal → "비용 관리 + 청구" → "예산" → 만들기 → 금액 약 $80, 경보 임계 50%/80%/100% → 알림 이메일 = 운영자 주소.
- **매주 1회** "비용 관리 → 비용 분석"에서 이번 달 누적·남은 크레딧을 눈으로 본다. 이 숫자가 §6(Oracle 이사)의 방아쇠다.
- 돈 아끼는 스위치: **파일럿이라 밤엔 안 쓴다면 VM을 꺼둔다**(Portal에서 VM "중지/할당 취소"). 꺼진 시간은 컴퓨팅 과금 안 됨(디스크 소액만). 단, VM이 꺼진 동안은 **Caddy 앞문도 죽어 공개 URL이 응답 안 함**(시연 링크 상시개방과 양립 불가). DNS 이름 레이블은 공용 IP 리소스에 붙어 있어 호스트네임 자체는 유지되지만, 껐다 켤 때 공용 IP가 바뀌면(동적 IP) 접속 전 Portal에서 IP를 재확인한다(호스트네임은 자동으로 새 IP를 가리킴).

---

### 2. 수동 vs 코드형(IaC) — 파일럿은 수동이 정답

**결론: 지금은 Portal로 손으로 만든다. IaC(Terraform 등) 도입 금지 — 과잉설계다.**

- IaC는 VM을 수십 대 반복 생성/폐기할 때 빛난다. 우리는 **VM 1대**다. 손으로 한 번 만드는 게 배우는 것보다 빠르다.
- **이미 코드화되어 우리를 지켜주는 것**(이게 진짜 IaC 자산):
  - `docker-compose.yml` + `deploy/Caddyfile` — 어떤 컨테이너가 어떻게 뜨는지. VM이 죽어도 이 파일 + `.env`만 있으면 **어디서든 30분 안에 컴퓨트 재현**(Oracle 이사가 쉬운 이유). ⚠️ 단 앞문의 공개 주소(Azure cloudapp 호스트네임)는 Azure 전용이라 다른 클라우드에선 `SITE_ADDRESS`·DNS를 다시 잡아야 한다.
  - `.env` — 비밀·설정 전부. 코드가 아니라 비밀이라 git에 안 올림(§7에서 따로 백업).
  - `backend/Dockerfile` — arm64 지원 이미지라 Oracle ARM에서도 그대로 뜸.
- **나중에(배포가 반복되면) 코드화 후보** — 지금은 하지 마라:
  - [ ] VM 초기 셋업(docker 설치·유저 생성)을 셸 스크립트 1장으로.
  - [ ] 백업 스케줄(cron) 등록 스크립트(§5, 위험대장 Phase 2 "백업 자동화 미등록").
  - 그 외 Terraform·Ansible·Kubernetes는 **연구원 수백 명 규모까진 불필요**(24_system_architecture §0 "없는 트래픽 대비 = 사망원인 1위").

---

### 3. 앞문 / DNS 관리 — Caddy + Azure cloudapp 호스트네임

우리 서비스의 공개 주소는 **Azure 공용 IP의 무료 DNS 호스트네임**(`polyinsight.japaneast.cloudapp.azure.com`)이고, HTTPS는 **Caddy 컨테이너**가 종단한다. 도메인 구매는 없다.

작동 방식 (왜 편한가):
- `caddy` 컨테이너(`caddy:2`)가 호스트 **80·443**을 열고(compose:41-43) Let's Encrypt로 인증서를 자동 발급·갱신해 `web:3000`으로 프록시한다(compose:37-51). → 도메인 0원, TLS 0원.
- ⚠️ 대가: **Azure 인바운드 80/443 개방 필요 + VM 공용 IP 직접 노출**(Cloudflare의 IP 은닉·기본 DDoS 방어는 없어짐). 인터넷 봇이 이 IP를 스캔한다.
- 발급된 인증서는 `caddy-data` 볼륨(compose:46)에 영속돼 재시작마다 재발급(Let's Encrypt 레이트리밋)되지 않는다.

설정이 어디 있나:
- 공개 FQDN = **`.env`의 `SITE_ADDRESS`** 한 줄(스킴 없이). caddy 서비스가 이 값으로 자동 HTTPS를 켠다(compose:40).
- 앞문 라우팅 = **`deploy/Caddyfile`** (`{$SITE_ADDRESS} { reverse_proxy web:3000 }`). compose는 이 파일을 read-only로 마운트(compose:45).
- 호스트네임의 근원 = Azure 공용 IP 리소스의 **DNS 이름 레이블**(`polyinsight`, 리전 Japan East). Portal → 공용 IP → Configuration에서 설정.

**공개 URL이 바뀌는 조건** — 바뀌면 사용자 접속 끊김 + 인증메일/OAuth 링크 깨짐:
- 공용 IP 리소스를 **삭제하고 새로 만들면** DNS 이름 레이블을 다시 붙여야 한다(같은 리전이면 같은 레이블 재사용 가능 → 같은 호스트네임 복구).
- **다른 클라우드(Oracle 등)로 이사**하면 cloudapp 호스트네임을 못 쓴다 → 앞문/도메인 재결정(§5-5).
- ⚠️ 공개 URL이 바뀌면 **`.env`의 `SITE_ADDRESS`·`PUBLIC_BASE_URL`·`ALLOWED_ORIGINS`(+ OAuth 콜백)를 같이 바꿔야** 인증서·인증메일 링크가 안 깨진다(config.py:78). `PUBLIC_BASE_URL` 미설정으로 https 배포하면 backend가 startup에서 크래시(main.py:43-44).

**HTTPS 배포 시 반드시 세팅**(안 하면 backend 컨테이너가 아예 안 뜸 — `_validate_prod_config`, main.py:33-46). 게이트가 켜지는 조건 = `ALLOWED_ORIGINS` 또는 `PUBLIC_BASE_URL` 중 하나라도 `https://`면 자동 감지(main.py:39):
- [ ] `.env`에 `SITE_ADDRESS=polyinsight.japaneast.cloudapp.azure.com`  (없으면 Caddy가 앞문을 못 켬)
- [ ] `.env`에 `COOKIE_SECURE=True`  (없으면 crash, main.py:42)
- [ ] `.env`에 `PUBLIC_BASE_URL=https://polyinsight.japaneast.cloudapp.azure.com`  (없으면 crash, main.py:44)
- [ ] `.env`에 `RENDER_TOKEN=<랜덤 긴 문자열>`  (없으면 crash, main.py:46)
  - 앱 게이트 셋(COOKIE_SECURE·PUBLIC_BASE_URL·RENDER_TOKEN) 중 하나라도 빠지면 startup 크래시(일부러 그렇게 막아둠 = fail-closed). `docker compose logs backend`에 한글 에러가 찍힌다.

**나중에 진짜 도메인 붙이는 법**(예: `polyinsight.kitech.re.kr`):
1. 도메인의 DNS(A 레코드)를 VM 공용 IP(20.210.112.15)로 가리킨다(또는 KITECH DNS에 A/CNAME 등록).
2. `.env`의 `SITE_ADDRESS`를 새 도메인으로 교체 → Caddy가 그 도메인으로 새 Let's Encrypt 인증서를 자동 발급.
3. `.env`의 `PUBLIC_BASE_URL`·`ALLOWED_ORIGINS`도 새 도메인으로 교체.
4. `docker compose up -d caddy backend`로 재기동. ⚠️ **`ALLOWED_ORIGINS`는 web 이미지에 빌드 시점에 굽지 않으니 backend만 재시작하면 됨. 단 `BACKEND_ORIGIN`처럼 web build-arg를 바꾸면 `--build`로 web 재빌드 필요**(compose:26-29).

---

### 4. 무엇을 감시 · 언제 손대나 (스케일 트리거)

**원칙: 지금은 단일 호스트·단일 프로세스로 충분하다(연구원 수백 명까지). 미리 키우지 마라.** 아래 신호가 **실제로 보일 때만** 움직인다.

일상 감시 (SSH 들어가서 30초):
```bash
docker compose ps          # 컨테이너 3개(backend/web/caddy) 다 Up 인가
free -h                    # 남는 메모리 (Chromium이 램 먹음)
df -h /                    # 디스크 여유 (꽉 차면 배포/렌더 실패)
docker stats --no-stream   # 컨테이너별 CPU/메모리 순간값
docker compose logs -f backend   # 렌더/저작 에러 실시간 (Ctrl+C로 빠져나옴)
```

무엇을 · 언제 · 터지면 뭐:

| 신호 (이게 보이면) | 원인 | 조치 |
|---|---|---|
| 덱 렌더 중 backend 컨테이너가 죽거나 재시작(OOM) | Chromium+Opus 큰 HTML이 RAM 초과 | **VM 크기 up**(Portal → VM → "크기" → 한 단계 위, 예 B2s→B2ms). VM 재부팅 필요, 몇 분 다운. 재부팅 후 `docker compose up -d` |
| `df -h`가 80%↑ | SQLite·자산 누적, docker 이미지 찌꺼기 | `docker system prune -f`(안 쓰는 이미지 정리) → 그래도 부족하면 디스크 확장 or Oracle 이사 |
| 저작(S6)/렌더 도는 동안 **접수·로그인까지 느림** | 웹과 렌더가 한 프로세스(24 §2 약점) | 사용자 체감될 정도로 자주면 → **L2(워커 분리)** 검토. 그 전엔 방치 OK |
| 재배포/재시작 후 **진행 중이던 덱이 실패(ERROR) 처리됨** | `recover_stale_jobs`가 startup에 PENDING/RUNNING을 ERROR로 회수(단일프로세스 전제, main.py:54 / db.py:453) | 지금은 "**배포 시 진행 중 작업 없을 때만 재배포**"로 회피. 자주 아프면 → **L2** |

**L2(웹/워커 분리)로 언제 가나** — 지금 가지 마라:
- 트리거 = 위 표의 마지막 두 줄이 **반복적으로** 아플 때. 위험대장(2026-07-09) **Phase 3~4**가 이 작업이고, 착수 전 하드 블로커(입력 PDF 미영속 C1, 큐 몰살 C2)를 먼저 풀어야 한다.
- 사용자 결정(risk register §3): **L2는 UI 작업 완료 후, 파이프라인 첫 생성만 큐로.** 지금은 범위 밖 — "그런 게 있다"만 알면 됨.

---

### 5. 재배포 전 필수 — 자산 소실 방지 (위험 C3, 지금 상태의 함정)

⚠️ **이 항목을 건너뛰면 재배포 한 번에 유저 업로드 자산이 영구 소실된다.** 현재 `docker-compose.yml`은 `/data` 볼륨(SQLite)만 마운트하고, **STORAGE_DIR(카드 PNG·export·유저 업로드 자산)은 컨테이너 안 경로**(`backend/var/blobstore`, config.py:35). 컨테이너를 새로 만들면 이게 사라진다.

- 사라지는 것 = 세 종류: **카드 PNG·export**(다시 렌더하면 복원됨, 단 재렌더 비용·시간 발생) + **유저 업로드 자산**(`jobs/*/assets/` — **복원 불가, 영구 소실**).

**배포 트리거 시 반드시 선행**(위험대장 결정 §3-3: "배포는 나중에, Phase 2는 배포 직전 필수"):
- [ ] `docker-compose.yml`의 backend `environment`에 `STORAGE_DIR=/data/blobstore` 추가 → 자산도 영속 볼륨(`/data`)에 들어감(C3 완화). 기존 `WEB_BASE_URL`·`DATABASE_URL` 옆에 한 줄(compose:10-12).
- [ ] `.env.example`·이 매뉴얼에 반영.
- [ ] `_validate_prod_config`에 STORAGE_DIR 영속성 확인 추가(위험 H5, main.py:33-46).
- [ ] `compose down` → `up -d` 한 뒤 **자산이 잔존하는지 실제로 확인**(H5 런북 E2E).

**재배포 안전 순서**(위험 H1 — 순서 안 지키면 자산 조용히 소실):
```
1) 백업 먼저 (아래 백업 명령)          ← down 전에
2) docker compose up -d --build         ← backend가 startup에 자동 migrate(main.py:53)
3) 로그인 + 덱 1개 열어 확인
```

**백업** (위험대장: "백업 자동화 미등록" — 지금은 수동, cron 등록 필요). 스크립트 = `backend/scripts/backup_db.py`:
```bash
# 컨테이너 안에서 실행. ★ --dest 로 /data(영속 볼륨)에 저장해야 재배포에도 남는다.
docker compose exec -T backend python -m backend.scripts.backup_db --dest /data/backups
```
- 이 스크립트가 만드는 것 = **DB 스냅샷**(`polyinsight_*.db`, VACUUM INTO + 무결성 사후검증, backup_db.py:43-79) + **자산 tar.gz**(`assets_*.tar.gz`, backup_db.py:82-100).
- ⚠️ **자산 tar에 담기는 건 유저 업로드(`jobs/*/assets/`)뿐**이다(backup_db.py:84). **카드 PNG(`cards/`)·export(`exports/`)는 TTL로 재생성 가능하므로 백업에서 일부러 제외.** → 이것들은 잃어도 재렌더로 복원, 유저 업로드만 백업으로 지킨다.
- ⚠️ **`--dest` 없이 실행하면 기본값 `backups/`가 컨테이너 안(`/app/backups`)에 생겨 재배포 때 같이 증발**한다. 항상 `--dest /data/backups`.
- ⚠️ **DB가 약 1MB 미만이면 `--min-bytes` 가드에 걸려 abort**(엉뚱한 빈 DB 방지, backup_db.py:48-49,107-108). 파일럿 초기 소형 DB면 `--min-bytes 100000` 붙여 실행.
- 복원은 **DB + 자산을 같은 시점 쌍으로**(backup_db.py 상단 복원 리허설 1~7단계). 어긋나면 DB의 storage_key와 실제 파일이 dangling.

- [ ] **매일 자동화**(아직 미등록): 리눅스 cron (`crontab -e`)
  ```
  0 3 * * * cd /path/to/polyinsight && docker compose exec -T backend python -m backend.scripts.backup_db --dest /data/backups >> /path/to/polyinsight/backup.log 2>&1
  ```
- [ ] `/data/backups`를 **VM 밖으로도** 주기적으로 복사(VM 통째로 날아가는 경우 대비). 예:
  ```bash
  # 노트북에서 — VM의 최신 백업을 끌어온다
  scp -r user@<공용IP>:/var/lib/docker/volumes/*polyinsight-data/_data/backups ./
  ```
  (볼륨 실경로가 헷갈리면 `docker compose exec backend ls /data/backups`로 파일명만 확인 후 `docker cp`로 꺼내도 됨.)

---

### 6. ★ 크레딧 소진 → Oracle ARM 무료 이사

**왜 (컴퓨트는) 쉬운가**: 배포가 통째로 `docker-compose.yml` + `deploy/Caddyfile` + `.env`에 담기고, `backend/Dockerfile`이 arm64 지원 이미지(`mcr.microsoft.com/playwright/python:v1.44.0-jammy`, Dockerfile:3)라 **Oracle Ampere(ARM)에서 backend·web·SQLite가 그대로 뜬다.** ⚠️ **앞문은 그대로가 아니다**: 지금 공개 주소는 Azure `cloudapp.azure.com` 무료 호스트네임이라 Oracle에선 못 쓴다 → 앞문/도메인을 새로 정하고(도메인 구매+Caddy / Cloudflare named 터널+도메인 / DuckDNS+Caddy) `.env`의 `SITE_ADDRESS`·`PUBLIC_BASE_URL`·`ALLOWED_ORIGINS` + DNS를 새로 잡아야 한다. **공개 URL이 바뀌면 인증메일·OAuth 링크도 갱신.**

**이사 트리거**(하나라도):
- Azure 비용 분석의 남은 크레딧이 약 $20 밑으로.
- 예산 경보 80% 이메일.
- 파일럿 끝나고 상시 운영 전환 결정(무료가 이득).

**이사 순서**:
- [ ] 1. Oracle Cloud 가입 → **Always Free ARM VM**(Ampere, 최대 4 OCPU·24GB) 생성, Ubuntu.
- [ ] 2. 새 VM에 docker + docker compose 설치.
- [ ] 3. **레포 + `.env` + `docker-compose.yml`을 새 VM으로 복사**(`.env`는 git에 없으니 §7 백업본에서 scp).
- [ ] 4. **데이터 이전** — 이게 핵심. 먼저 §5의 STORAGE_DIR 볼륨 조치가 되어 있어야 자산까지 옮겨진다.
  - Azure VM에서: `docker compose exec -T backend python -m backend.scripts.backup_db --dest /data/backups` → DB+자산 스냅샷 쌍 생성.
  - 그 스냅샷 쌍(`polyinsight_*.db` + `assets_*.tar.gz`)을 새 VM으로 `scp`.
  - 새 VM에서 compose 한 번 떠서 볼륨 생성 후, **복원 리허설**(backup_db.py 1~7단계): backend 정지 → DB를 `/data/polyinsight.db`로 복사 → `assets_*.tar.gz`를 STORAGE_DIR(`/data/blobstore`)에 풀기 → backend 기동 → 로그인 확인.
- [ ] 5. **새 앞문 세팅(★열린 결정)** — Oracle엔 Azure cloudapp 호스트네임이 없다. 앞문 옵션을 하나 고른다: ⓐ 도메인 구매 후 그 도메인 A레코드를 Oracle VM 공용 IP로 → `SITE_ADDRESS`=그 도메인(Caddy가 Let's Encrypt 발급), ⓑ Cloudflare named 터널+도메인, ⓒ DuckDNS 등 무료 동적 DNS+Caddy. 고른 뒤 새 VM `.env`의 `SITE_ADDRESS`·`PUBLIC_BASE_URL`·`ALLOWED_ORIGINS`(+ OAuth 콜백)를 새 주소로 맞춘다. 공개 URL이 바뀌므로 인증메일 링크·시연 링크를 새로 안내.
- [ ] 6. 새 VM에서 `docker compose up -d --build`. 사용자 접속·덱 1개 열림 확인.
- [ ] 7. **전환(컷오버) 주의**: 새 VM 검증이 끝나면 공개 주소(DNS)를 새 Oracle 앞문으로 넘긴다. Azure는 앞문만 내려(`docker compose stop caddy`) 트래픽을 끊되 데이터는 롤백용으로 며칠 보존. (Azure↔Oracle은 주소가 다르니 트래픽이 자동으로 안 갈린다 — DNS/링크 안내를 새 주소로 바꾸는 시점이 컷오버다.)
- [ ] 8. 안정 확인 후 Azure 리소스 그룹 삭제(과금 종료). **삭제 전 마지막 백업 한 벌을 VM 밖에 보관.**

---

### 7. 문서·지식 관리 & bus factor

**bus factor = 운영자(너)가 갑자기 사라져도 다음 사람이 복구할 수 있나.** 지금은 1명이라 취약하다. 아래 최소 기록만 있으면 남이 30분 안에 서비스를 되살릴 수 있다.

**어딘가 안전한 곳(1Password/암호화 메모/박사님과 공유 드라이브)에 보관** — git에 올리지 말 것:
- [ ] `.env` 파일 **통째로 백업**(`SITE_ADDRESS`·`RENDER_TOKEN`·`ANTHROPIC_API_KEY`·`RESEND_API_KEY`·`PUBLIC_BASE_URL` 등 전부). 서버 잃으면 이 파일이 서비스의 심장.
- [ ] **Azure 리소스 이름들**: 리소스 그룹명, VM명, 공용 IP, 리전.
- [ ] **앞문(Azure) 위치**: 공용 IP(20.210.112.15), 공용 IP의 DNS 이름 레이블(`polyinsight`, 리전 Japan East), 리소스 그룹명(`polyinsight`), NSG 규칙(22·80·443). 앞문 설정 = `deploy/Caddyfile` + `.env`의 `SITE_ADDRESS`.
- [ ] **Anthropic 콘솔 계정**(Opus 키 재발급·사용량·비용 확인처) + **Resend 계정**(이메일).
- [ ] SSH 접속법: `ssh user@<공용IP>` + 키 파일 위치.
- [ ] 복구 한 줄 요약: "레포 clone → `.env` 복원 → `docker compose up -d --build` → 백업 DB·자산 복원(§5)".

**이 매뉴얼을 최신으로 유지하는 규칙** (인프라 변경 = 문서 변경, 프로젝트 CLAUDE.md §4 "docs 먼저"):
- [ ] compose·Dockerfile·`.env` 스키마를 바꾸면 → **같은 커밋에서** 이 매뉴얼의 해당 표/명령을 고친다.
- [ ] VM 크기·리전·공개 도메인(`SITE_ADDRESS`)을 바꾸면 → §1·§3 값과 §7 기록장 갱신.
- [ ] Azure→Oracle 이사를 하면 → §0·§1을 Oracle 기준으로 갈아엎고 제목 옆에 "호스트=Oracle" 표기.
- [ ] 위험대장에서 C3(STORAGE_DIR 볼륨)·백업 cron이 **해결되면** → §5의 ⚠️ 경고를 "완료"로 바꾼다. 해결 전까진 경고 유지.
- [ ] **변경 이력 표**를 이 문서 맨 아래 두고, 인프라 만지는 날마다 한 줄 추가(날짜·무엇·왜).

> 한 줄 원칙: **"서버에서 손으로 바꾼 것은 반드시 `.env`/compose/이 문서 셋 중 하나에 적힌다."** 서버에만 있고 어디에도 안 적힌 변경은 다음 재배포 때 사라지거나, 다음 사람이 영원히 모른다.

---

*(근거 파일: `docker-compose.yml`, `backend/Dockerfile`, `backend/core/config.py`, `backend/main.py`, `backend/scripts/backup_db.py`, `docs/contracts/24_system_architecture.md`, `docs/superpowers/plans/2026-07-09-candidates-risk-register-and-roadmap.md` C1·C2·C3·H1·H5.)*

---

## 10. 보완 필요 (섹션에 안 담겼거나 흩어진 필수 항목)

> 완결성 비평이 잡은 "이 매뉴얼이 아직 약한 곳". 박사님 전달 전 이것부터 메운다.

### 10-1. 이메일 (로그인 안 막힘 · 실제 영향 = 업로드 상한 + 비번재설정)
> ⚠️ **정정**: 초안은 "로그인 자체가 막힘"이라 썼으나 **사실이 아니다.** 우리 인증은 **grace 모드(비차단)** — 가입하면 이메일 인증 없이 자동로그인→대시보드(`auth.py:168` 헤더, `db.py:198` "grace라 비차단"). `email_verified`가 실제로 문을 막는 곳은 **업로드 쿼터 한 곳뿐**(`ratelimit.py:76`).

지금 Resend가 **테스트모드**(`EMAIL_FROM=onboarding@resend.dev`)라 외부 주소로 **가입 인증메일·비번재설정 메일이 안 도착**한다. 미인증의 실제 영향은 딱 2개:
1. **업로드 하루 3개 상한**(인증 시 20 — `UPLOAD_UNVERIFIED_LIMIT` vs `UPLOAD_USER_LIMIT`).
2. **비번 분실 시 자가 재설정 불가**(재설정 메일이 안 감 → 운영자가 `seed_user`로 처리).

- **소수 지인 파일럿(권장)**: 박사님이 직접 가입 → 운영자가 `docker compose exec backend python -m backend.scripts.seed_user 박사님이메일 아무거나`로 인증(상한 해제, 비번 미변경). 비번사고도 같은 도구로.
- **외부 정식 공개 때만**: 도메인 사서 Resend DKIM 검증 → `EMAIL_FROM` 교체 → 외부 주소 실발송 1회 확인.

### 10-2. Anthropic 하드 스펜드캡 (돈 새는 걸 막는 유일한 자동장치)
비용 섹션은 덱당 비용을 **추정**만 한다. 오픈 가입이라 악성/실수로 다량 생성되면 변동비가 상한 없이 는다. → **console.anthropic.com 워크스페이스에 월 지출 상한 + 청구 경보**를 반드시 건다. (앱의 업로드 쿼터는 1차 방어, 이건 최종 안전판)

### 10-3. 개인정보·저작권 (파일럿이라도 최소선)
- 업로드 PDF = **타인 저작물**(논문). 파일럿 참가자에게 "본인이 볼 권한 있는 논문만 업로드" 고지.
- 회원 이메일·세션 = **개인정보**. 파일럿 참가 동의 1줄, **탈퇴/삭제 요청 처리법**(해당 유저 job·계정 삭제 = `delete_job` + 계정 row) 정해둔다.

### 10-4. 박사님 온보딩 + 자격증명 인수인계 + SLA 고지 (bus factor)
- **계정 발급**: 박사님 계정 만들어 전달(§10-1).
- **한계 고지(중요)**: 단일 호스트·단일 프로세스 → **무중단 아님**, 재배포/재부팅 시 진행 중 덱 생성이 실패할 수 있음. "완제품 아니라 파일럿"임을 미리 문서로 공유해 기대치 맞춘다.
- **인수인계 봉투**(운영자 부재 대비): `.env` 사본 위치, SSH 키, Azure/Anthropic/Resend 콘솔 계정, Azure 공용 IP·DNS 레이블(`polyinsight`)·리소스 그룹명을 한곳에 정리(암호화). 이걸 잃으면 아무도 못 고친다.

### 10-5. 로그 로테이션 (디스크풀 방지)
`run.log`와 docker json 로그가 무한 증식 → 디스크풀 → 렌더/배포 실패. 30GB 디스크에서 실제 위험.
- docker 로그 상한: compose 각 서비스에 `logging: { driver: json-file, options: { max-size: "10m", max-file: "3" } }` 추가.
- `run.log`는 주기적 truncate 또는 `logrotate` 등록.

### 10-6. Azure 계정 보안 (실제 앞문·컨트롤플레인)
앞문이 Cloudflare에서 **Azure(공용 IP·NSG·cloudapp 호스트네임) + Caddy**로 바뀌었다. 이제 컨트롤플레인은 Azure 계정이다. VM만 지키고 Azure 계정이 뚫리면 무력.
- Azure 계정 **2FA(MFA) 필수**. NSG를 함부로 못 바꾸게 최소 권한.
- **인증서는 Caddy가 자동 갱신** — 별도 만료 관리 불필요. 단 갱신 실패(NSG 80 닫힘 등) 대비해 §7-3 SSL 모니터로 감시.
- 나중에 진짜 도메인을 사면 그 **도메인 소유·만료 관리**(레지스트라 2FA)가 추가된다.

### 10-7. 배포 브랜치·버전 확정
현재 작업 브랜치 `feat/emerald-redesign`가 `main`보다 **약 143커밋 앞섬**(위험대장). 배포 시 **어느 브랜치/커밋**을 올리고 롤백 시 **어느 커밋**으로 되돌릴지 못 박아라(태그 권장: 배포마다 `git tag deploy-YYYYMMDD`).

---

## 11. 네가 정할 것 (열린 결정 — 정하는 대로 이 문서에 박기)

| # | 결정 | 선택지 · 기본 권장 |
|---|---|---|
| D1 | **VM 크기 + 동시성** | B2s(2vCPU/4GB, 약 $33/월) 기본. 4GB라 Chromium OOM 방지로 `.env`에 `MAX_CONCURRENT_JOBS=2~3`. 여유 원하면 B2ms(약 $60, runway↓) |
| D2 | **켜둠 정책** | 파일럿 기본 = **항상 켜짐**(박사님 아무때나 접속, ~3개월 runway). 크레딧 아끼려 `az vm deallocate`하면 **앞문·공개 URL도 죽음**(VM이 꺼지면 Caddy도 정지) → 박사님과 "데모 창" 합의 필요 |
| D3 | **비용 상한 금액** | Anthropic 월 캡·Azure 예산 금액. 덱 1건 실측(§5) 후 확정. 예: Anthropic $50, Azure $80 |
| D4 | **주소** | **결정됨(2026-07-13)**: Azure 무료 호스트네임 `polyinsight.japaneast.cloudapp.azure.com` + Caddy(Let's Encrypt). 남은 결정 = ⓐ 나중에 KITECH 진짜 도메인(`polyinsight.kitech.re.kr` 등) 붙일지 접근권 확인, ⓑ Oracle 이사 시 앞문 재결정(§5-5) |
| D5 | **이메일** | 테스트모드+계정 미리인증(소수) vs 도메인 DKIM 검증(제대로) — §10-1 |
| D6 | **백업 오프사이트** | 목적지(노트북 scp / Azure Blob / Oracle Object) + 주기(일 03:00) + 보존(7~30일) + gpg 암호구절 보관처 |
| D7 | **.env 보관처** | 비번매니저 / 암호화 USB / Key Vault + 로테이션 책임자 |
| D8 | **업로드 쿼터** | 기본 20/일 유지 vs 파일럿용 낮춤(`UPLOAD_USER_LIMIT=5`) |
| D9 | **이사 시점** | 크레딧 소진 임박 트리거로 Oracle ARM 이사 vs 파일럿 끝까지 Azure |

---

## 12. 이 문서가 채택한 기준 (섹션 간 불일치 정리)

섹션별로 숫자·지침이 달랐던 것을 아래로 통일한다(섹션 본문과 충돌 시 **이 표 우선**):

- **비용/러너웨이**: **B2s 항상켜짐 ≈ 약 $33/월 → $100 크레딧 ≈ 약 3개월**(리전따라 ±). 예산·경보 금액의 기준선.
- **C3(STORAGE_DIR 볼륨) 조치 정본 = §6 배포.** §5·§8·§9는 경고·링크만. 한 번만 고치면 됨.
- **MAX_CONCURRENT_JOBS**: B2s(4GB)면 OOM 방지로 `.env`에 **2~3** 권장 — 배포 시 반영(§6에 반영).
- **켜둠 정책**: 파일럿 기본 **항상 켜짐**(D2). deallocate는 URL 죽이므로 크레딧 절약과 상시 데모는 양립 불가 — 하나 골라야 함.
- **인프라 상태 기준**: 모든 절차는 **C3 조치 후**(blobstore가 `/data` 볼륨에 있음) 상태를 전제한다.

---

## 13. 변경 이력

| 날짜 | 버전 | 요약 |
|---|---|---|
| 2026-07-13 | v1.0 | 신규. 6축 운영 진단 워크플로(보안·비용·배포·모니터링·백업DR·인프라생애) → 운영 매뉴얼. 실스택 file:line 근거. §1 우선순위·§2 캘린더·§3 응급런북·§10 보완·§11 열린결정·§12 기준통일. |
| 2026-07-13 | v1.1 | **앞문 교체: cloudflared 터널 → Caddy 리버스 프록시.** 공개 URL = `https://polyinsight.japaneast.cloudapp.azure.com`(Azure 무료 DNS 호스트네임, 도메인 미구매). Caddy(`caddy:2`)가 인바운드 80·443 직접 수신 + Let's Encrypt 자동 HTTPS → `web:3000` 프록시(`deploy/Caddyfile`). `TUNNEL_TOKEN` 폐기·`SITE_ADDRESS` 신규. **보안 서사 변경**: NSG 22·80·443 개방, VM 공용 IP(20.210.112.15) 직접 노출, Cloudflare IP은닉·DDoS방어 상실. 트러블슈팅(cloudflared→caddy 로그)·비용·NSG·env표·§9-3 앞문관리·Oracle이사(앞문=열린결정) 전면 갱신. 근거: 퀵터널 URL 불안정+named터널 도메인 유료(거부) → Azure 무료 호스트네임+Caddy 무료 TLS로 고정+무료+HTTPS 확보(트레이드오프: 인바운드 80/443 개방 수용). |
