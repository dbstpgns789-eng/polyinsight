import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI


# Windows에서 Playwright subprocess 실행에 ProactorEventLoop 필요
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from fastapi.middleware.cors import CORSMiddleware

from backend.core import ratelimit
from backend.core.auth import get_current_user
from backend.core.config import settings
from backend.core.db import cleanup_expired_blobs, migrate, recover_stale_jobs
from backend.routers import auth, deck, export, images, jobs, projects


def _setup_file_logging() -> None:
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%H:%M:%S",
    )
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fh = logging.FileHandler("run.log", encoding="utf-8")
    fh.setFormatter(fmt)
    root.addHandler(fh)


def _validate_prod_config() -> None:
    """HTTPS 배포(https 오리진 감지)면 fail-closed로 필수 보안 설정 강제. dev(http)는 무영향.
    DEBUG는 dev에서도 False라 신뢰 불가 → https 오리진 유무가 유일한 prod 신호."""
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    if settings.PUBLIC_BASE_URL:
        origins.append(settings.PUBLIC_BASE_URL)
    if not any(o.startswith("https://") for o in origins):
        return  # http-only = 로컬 dev, 강제 안 함
    if not settings.COOKIE_SECURE:
        raise RuntimeError("HTTPS 배포인데 COOKIE_SECURE=False — 세션 쿠키 Secure 누락. .env에 COOKIE_SECURE=True 설정.")
    if not settings.PUBLIC_BASE_URL:
        raise RuntimeError("HTTPS 배포인데 PUBLIC_BASE_URL 미설정 — 인증메일 링크가 내부호스트로 깨짐.")
    if not settings.RENDER_TOKEN:
        raise RuntimeError("HTTPS 배포인데 RENDER_TOKEN 미설정 — 내부 렌더 우회 토큰 필수.")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_file_logging()   # uvicorn 핸들러 설정 완료 후 FileHandler 추가
    _validate_prod_config()  # 프로덕션 필수 보안 설정 fail-closed 검증
    await migrate()
    recovered = await recover_stale_jobs()
    if recovered:
        logging.getLogger(__name__).info("stale job %d건 ERROR로 회수 (서버 재시작 고아)", recovered)
    task = asyncio.create_task(_ttl_cleaner())
    try:
        yield
    finally:
        task.cancel()


async def _ttl_cleaner():
    try:
        while True:
            await asyncio.sleep(1800)
            await cleanup_expired_blobs()
            ratelimit.sweep()  # rate limit 카운터 회수(메모리 무한증식 방지)
    except asyncio.CancelledError:
        return


app = FastAPI(title="PolyInsight", version="2.0.0", lifespan=lifespan)


@app.middleware("http")
async def _security_headers(request, call_next):
    """HTTPS 배포(COOKIE_SECURE)에서만 HSTS — SSL-strip 방어. http dev엔 미전송."""
    resp = await call_next(request)
    if settings.COOKIE_SECURE:
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return resp


_cors_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    # 심층방어용 — 실제 요청은 Next rewrite로 프록시돼 same-origin이라 CORS는 라이브 경로에 안 걸림.
    # 직접 브라우저→백엔드 오리진이 생길 경우 대비. 쿠키 인증이라 와일드카드 금지(자격증명 비호환).
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.include_router(auth.router)
app.include_router(jobs.router, dependencies=[Depends(get_current_user)])
app.include_router(projects.router, dependencies=[Depends(get_current_user)])
app.include_router(export.router, dependencies=[Depends(get_current_user)])
app.include_router(images.router, dependencies=[Depends(get_current_user)])
app.include_router(deck.router)  # 단일 저작 경로 (헌법 v3.0) — 자체 get_current_user 의존
