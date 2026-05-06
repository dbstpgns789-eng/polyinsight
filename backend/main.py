import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.core.db import cleanup_expired_blobs, migrate


@asynccontextmanager
async def lifespan(app: FastAPI):
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
# TODO: routers will be registered here in Phase 5
