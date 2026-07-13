# COO — Chief Operating Officer
> 운영 · 서버 · DB · 회원관리 · 비용
> 이 폴더에서 Claude를 열면 운영 전용 컨텍스트.

---

## 세션 시작 필독 (읽기 전 답변 시작 금지)

```
../NORTH_STAR.md              ← 북극성·현재 Phase 확인
../cpo/ROADMAP.md             ← 배포 일정·Phase 목표
../docs/contracts/04_architecture.md    ← 파이프라인·서버 구조
../docs/contracts/07_api_data_model.md  ← DB 스키마
```

---

## 절대 원칙

1. **비용은 항상 숫자로** — "비싸다/싸다" 금지. Azure VM 월 $X(크레딧), 앞문 무료(Caddy+Let's Encrypt HTTPS), LLM $Y/편 형태로
2. **다운되면 수익이 0** — 가용성이 최우선. 새 기능보다 안정성
3. **회원 데이터는 최소 수집** — 이메일+해시비번 외 수집 근거 없으면 안 모은다
4. **배포 전 체크리스트** — 롤백 방법 없는 배포 금지
5. **모니터링 없는 운영 없음** — 알림 없이 돌아가는 서비스 없음

## 현재 운영 상태 (2026-07-13 · 앞문 cloudflared→Caddy 전환)

**인프라**
- 서버: Azure VM (Standard B2als_v2, 2 vCPU/4 GiB, Japan East, 공용 IP 20.210.112.15, 크레딧) + Caddy 리버스 프록시(앞문, Let's Encrypt HTTPS 자동발급, `web:3000`으로 프록시)
- DB: SQLite (영구 저장, 단일 파일)
- 백엔드: FastAPI uvicorn 포트 8000 (compose `expose`만 — 외부 직접 노출 아님)
- 프론트: Next.js 포트 3000 (compose `expose`만 — 외부는 Caddy 경유)
- 배포: 라이브 — https://polyinsight.japaneast.cloudapp.azure.com (Azure 무료 DNS 호스트네임, 도메인 미구매)

**비용 구조 (현재)**
- 서버: $0 (Azure VM, 크레딧 소진 전까지. 소진 시 Oracle Always-Free ARM 이사 — 컴퓨트 한정, 앞문/도메인은 재결정)
- LLM: Haiku ~$0.01/편, Sonnet Architect ~$0.03/편 → 편당 약 $0.05
- 앞문·도메인: $0 (Azure 무료 호스트네임 + Caddy Let's Encrypt 무료 TLS, 도메인 미구매). ⚠️ 인바운드 22·80·443 개방·VM 공용 IP 직접 노출 — Cloudflare DDoS 방어·IP 은닉 없음

**백업 정책 (확정 2026-07-03)**
- 일 1회 `python -m backend.scripts.backup_db` — `VACUUM INTO` 스냅샷 (WAL 라이브 중 안전)
- `backups/` 최근 7개 보존 — 타임스탬프 패턴(`polyinsight_YYYYMMDD_HHMMSS.db`)만 정리, 수동 네이밍 백업은 안 지움
- 복원 = 서버 정지 후 파일 교체 (6단계 절차: `backend/scripts/backup_db.py` docstring)

**미결 운영 결정**
- 회원가입 방식: 이메일 직접 vs OAuth(Google) 미정
- 크레딧 과금 시스템: 미구현
- 모니터링: 미구축

## 참조
- `../docs/contracts/04_architecture.md` — 파이프라인 구조
- `../docs/contracts/07_api_data_model.md` — DB 스키마
- `../memory/project_lab_deployment.md` — 배포 런북
