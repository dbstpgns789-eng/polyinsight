from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class CardStatus:
    card: int
    status: str = "pending"  # pending | rendering | done | error
    size_kb: int = 0
    png_bytes: bytes | None = None


@dataclass
class ExportJobRecord:
    export_job_id: str
    job_id: str
    status: str = "pending"  # pending | rendering | done | error
    cards: list[CardStatus] = field(
        default_factory=lambda: [CardStatus(card=i) for i in range(1, 6)]
    )
    zip_bytes: bytes | None = None
    error_card: int | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(hours=24)
    )


class ExportStore:
    def __init__(self) -> None:
        self._jobs: dict[str, ExportJobRecord] = {}

    def create(self, export_job_id: str, job_id: str) -> ExportJobRecord:
        record = ExportJobRecord(export_job_id=export_job_id, job_id=job_id)
        self._jobs[export_job_id] = record
        return record

    def get(self, export_job_id: str) -> ExportJobRecord | None:
        return self._jobs.get(export_job_id)

    def delete(self, export_job_id: str) -> None:
        self._jobs.pop(export_job_id, None)

    def purge_expired(self) -> int:
        now = datetime.utcnow()
        expired = [eid for eid, r in self._jobs.items() if r.expires_at < now]
        for eid in expired:
            del self._jobs[eid]
        return len(expired)


# Module-level singleton — imported by routes and agents
export_store = ExportStore()
