# 배포 런북 — Oracle Always Free VM + Cloudflare Tunnel (Plan 3)

> 상위 스펙: `docs/superpowers/specs/2026-06-15-lab-deployment-design.md`
> 코드/아티팩트는 완성됨(Dockerfile·compose·env). 이 문서는 **서버 확보 후** 실행하는 절차다.
> ⚠️ Docker 빌드는 로컬(Windows/x64)에서 검증 불가 → 서버(ARM64)에서 첫 빌드 시 한두 줄 조정 가능성 있음. 그 지점은 아래에 표시.

---

## 아티팩트 목록 (이미 리포에 있음)

| 파일 | 역할 |
|---|---|
| `backend/Dockerfile` | FastAPI + Playwright/Chromium (arm64) |
| `web/Dockerfile` | Next.js standalone |
| `docker-compose.yml` | web + backend + cloudflared 3-서비스 |
| `.env.example` | 환경변수 템플릿 |
| `.dockerignore` | 빌드 컨텍스트 제외 |

핵심 결선:
- `web` rewrite `/api/*` → `BACKEND_ORIGIN=http://backend:8000`
- `backend` Playwright → `WEB_BASE_URL=http://web:3000`
- 외부 노출은 `cloudflared`가 `web:3000` 한 곳만 (인바운드 포트 개방 0)

---

## 0. 사전 준비 (확보 완료 가정)

- Oracle Always Free **Ubuntu 22.04 ARM VM** (Public IP, SSH 접속됨)
- 도메인 1개 (Cloudflare에 등록되어 있어야 터널 hostname 연결 가능)
  - 도메인 없으면: Cloudflare에서 무료 등록 가능한 방법 or `*.cfargotunnel.com` 대신 커스텀 도메인 필요. **도메인은 박사님께 제공할 URL이 됨.**

---

## 1. VM에 Docker 설치

SSH 접속 후:

```bash
sudo apt-get update && sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker $USER && newgrp docker
docker --version && docker compose version
```

## 2. 코드 가져오기

```bash
git clone <레포 URL> polyinsight && cd polyinsight
git checkout feat/lab-deploy-auth     # (병합 전이면) 또는 병합된 main
```

## 3. 환경변수 설정

```bash
cp .env.example .env
nano .env
```
채울 값:
- `ANTHROPIC_API_KEY` = 운영자 키
- `COOKIE_SECURE=True`  ← 터널 HTTPS라 필수
- `RENDER_TOKEN=$(openssl rand -hex 16)` 값으로 채우기 (랜덤)
- `TUNNEL_TOKEN` = (4번에서 발급)
- (선택) `NEXT_PUBLIC_POSTHOG_KEY` = PostHog 프로젝트 키

## 4. Cloudflare Tunnel 생성 (대시보드)

1. Cloudflare **Zero Trust → Networks → Tunnels → Create a tunnel** → "Cloudflared" 선택
2. 터널 이름 지정 → **터널 토큰** 복사 → `.env`의 `TUNNEL_TOKEN`에 붙여넣기
3. **Public Hostname** 추가:
   - Subdomain/Domain: 박사님께 줄 URL (예: `polyinsight.<도메인>`)
   - Service: **Type=HTTP, URL=`web:3000`**  ← compose 네트워크의 web 서비스
4. 저장

## 5. 빌드 & 기동

```bash
docker compose build      # ⚠️ 첫 빌드 검증 포인트 (아래 트러블슈팅 참고)
docker compose up -d
docker compose ps         # 3개 서비스 Up 확인
docker compose logs -f web backend
```

## 6. 박사님 계정 + 초대코드 발급

```bash
# 컨테이너 안에서 시드 (DATABASE_URL은 compose가 /data로 설정)
docker compose exec backend python -m backend.scripts.seed_user doc@kitech.re.kr <비밀번호>
docker compose exec backend python -m backend.scripts.create_invite   # 향후 멤버용
```

## 7. 검증 (E2E)

1. 브라우저에서 `https://polyinsight.<도메인>` → `/login`으로 가는지
2. 시드 계정으로 로그인 → 대시보드 진입
3. **논문 PDF 업로드 → 카드 생성 → PNG 렌더 정상 확인** ← 렌더 토큰/Next rewrite 통과 핵심 검증
4. export 다운로드 확인
5. (PostHog 켰으면) 대시보드에 세션 잡히는지

## 8. 비용 가드레일 (잊지 말 것)

- Anthropic 콘솔에서 **월 사용 한도(usage limit)** 설정 → 키 폭주 방어
- `docker compose exec backend python -c "import asyncio; from backend.core import db; print(asyncio.run(db.list_events(20)))"` 로 토큰/비용 이벤트 확인 가능

---

## 로컬 Docker E2E 검증 결과 (2026-06-15)

서버 전에 로컬 compose(x64)로 빌드~E2E를 돌려 검증함. 인증(쿠키 through rewrite) + **렌더 토큰 풀루프(image_count=1)** 통과. 그 과정에서 잡은 버그 2건은 이미 수정됨:
- `requirements.txt`: `pymupdf4llm` 누락 + PyMuPDF 핀 불일치 → 백엔드 import 크래시 (수정)
- `BACKEND_ORIGIN`: Next는 `rewrites()`를 빌드 시점에 구움 → 런타임 env 무시 → **build arg로 전달**(web/Dockerfile + compose) (수정)

→ ARM 서버에서도 거의 동일하게 동작 예상. 아래는 잔여 조정 가능 지점.

## 트러블슈팅 (첫 빌드 조정 가능 지점)

- **web standalone 경로**: `web/Dockerfile` run 스테이지의 `server.js` 위치가 모노레포에선 `web/server.js`가 아닐 수 있음. 빌드 후 `docker run --rm <web이미지> ls`로 server.js 실제 경로 확인 → CMD 한 줄 조정.
- **ARM 용량/빌드 느림**: Playwright 이미지(arm64)는 크다(~2GB). 첫 빌드 수 분 소요 정상.
- **쿠키 미저장**: 로그인되는데 새로고침 시 풀리면 → `COOKIE_SECURE` 값과 터널 HTTPS 여부 점검.
- **렌더 401/빈 PNG**: `RENDER_TOKEN`이 `.env`에 있고 컨테이너 재기동됐는지 확인(백엔드 env와 Playwright 컨텍스트는 같은 프로세스라 자동 일치).

## 운영

```bash
docker compose pull && docker compose up -d --build   # 코드 업데이트 후 재배포
docker compose logs -f                                 # 로그
docker compose down                                    # 중지 (데이터 볼륨은 유지)
```

데이터(SQLite)는 `polyinsight-data` 볼륨에 영속 → `down` 해도 보존.
