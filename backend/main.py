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
from backend.core.db import cleanup_expired_blobs, migrate
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_file_logging()   # uvicorn 핸들러 설정 완료 후 FileHandler 추가
    await migrate()
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
