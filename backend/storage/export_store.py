"""
ExportStore — in-memory store for PNG export jobs.

ExportJob은 Playwright 렌더링 진행 중에만 필요한 단기 상태다.
완료된 ZIP bytes는 SQLite(exports 테이블)에 저장되므로
프로세스 재시작 후에는 download API에서 DB를 조회한다.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from ..core.models import CardRenderStatus, ExportJob


class ExportStore:
    def __init__(self, ttl_hours: int = 24) -> None:
        self._jobs: Dict[str, ExportJob] = {}
        self._ttl = timedelta(hours=ttl_hours)
        self._lock = asyncio.Lock()

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create(self, export_job_id: str, job_id: str, card_count: int = 5) -> ExportJob:
        job = ExportJob(
            export_job_id=export_job_id,
            job_id=job_id,
            cards={i: CardRenderStatus.PENDING for i in range(1, card_count + 1)},
            created_at=datetime.now(timezone.utc),
            zip_ready=False,
            error=None,
        )
        async with self._lock:
            self._jobs[export_job_id] = job
        return job

    async def get(self, export_job_id: str) -> Optional[ExportJob]:
        async with self._lock:
            return self._jobs.get(export_job_id)

    async def set_card_status(
        self,
        export_job_id: str,
        card_num: int,
        status: CardRenderStatus,
    ) -> None:
        async with self._lock:
            job = self._jobs.get(export_job_id)
            if job:
                job.cards[card_num] = status

    async def set_done(self, export_job_id: str) -> None:
        async with self._lock:
            job = self._jobs.get(export_job_id)
            if job:
                job.zip_ready = True

    async def set_error(self, export_job_id: str, message: str) -> None:
        async with self._lock:
            job = self._jobs.get(export_job_id)
            if job:
                job.error = message

    async def delete(self, export_job_id: str) -> None:
        async with self._lock:
            self._jobs.pop(export_job_id, None)

    # ── 상태 조회 헬퍼 ────────────────────────────────────────────────────────

    async def is_all_done(self, export_job_id: str) -> bool:
        job = await self.get(export_job_id)
        if not job:
            return False
        return all(s == CardRenderStatus.DONE for s in job.cards.values())

    async def has_error(self, export_job_id: str) -> bool:
        job = await self.get(export_job_id)
        if not job:
            return False
        return any(s == CardRenderStatus.ERROR for s in job.cards.values())

    async def done_card_nums(self, export_job_id: str) -> list[int]:
        job = await self.get(export_job_id)
        if not job:
            return []
        return [n for n, s in job.cards.items() if s == CardRenderStatus.DONE]

    # ── TTL 정리 (백그라운드 태스크에서 주기적으로 호출) ──────────────────────

    async def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        async with self._lock:
            expired = [
                eid for eid, job in self._jobs.items()
                if now - job.created_at > self._ttl
            ]
            for eid in expired:
                del self._jobs[eid]
        return len(expired)


# 싱글톤 — FastAPI lifespan에서 임포트해 사용
export_store = ExportStore()
