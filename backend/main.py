import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI


# Windows에서 Playwright subprocess 실행에 ProactorEventLoop 필요
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from fastapi.middleware.cors import CORSMiddleware

from backend.core.db import cleanup_expired_blobs, migrate
from backend.routers import export, jobs, projects


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
    except asyncio.CancelledError:
        return


app = FastAPI(title="PolyInsight", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router)
app.include_router(projects.router)
app.include_router(export.router)
