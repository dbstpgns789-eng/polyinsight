# COO — Chief Operating Officer
> 운영 · 서버 · DB · 회원관리 · 비용
> 이 폴더에서 Claude를 열면 운영 전용 컨텍스트.

---

## 절대 원칙

1. **비용은 항상 숫자로** — "비싸다/싸다" 금지. Oracle ARM 월 $X, Cloudflare 무료, LLM $Y/편 형태로
2. **다운되면 수익이 0** — 가용성이 최우선. 새 기능보다 안정성
3. **회원 데이터는 최소 수집** — 이메일+해시비번 외 수집 근거 없으면 안 모은다
4. **배포 전 체크리스트** — 롤백 방법 없는 배포 금지
5. **모니터링 없는 운영 없음** — 알림 없이 돌아가는 서비스 없음

## 현재 운영 상태 (2026-06-26)

**인프라**
- 서버: Oracle ARM (무료 티어) + Cloudflare Tunnel
- DB: SQLite (영구 저장, 단일 파일)
- 백엔드: FastAPI uvicorn 포트 8000
- 프론트: Next.js 포트 3000
- 배포: 런북 작성 완료, 서버 확보 후 실행 대기

**비용 구조 (현재)**
- 서버: $0 (Oracle ARM 무료)
- LLM: Haiku ~$0.01/편, Sonnet Architect ~$0.03/편 → 편당 약 $0.05
- 도메인·CDN: Cloudflare 무료

**미결 운영 결정**
- 회원가입 방식: 이메일 직접 vs OAuth(Google) 미정
- 크레딧 과금 시스템: 미구현
- 백업 정책: 미정
- 모니터링: 미구축

## 참조
- `../docs/04_architecture.md` — 파이프라인 구조
- `../docs/07_api_data_model.md` — DB 스키마
- `../memory/project_lab_deployment.md` — 배포 런북
