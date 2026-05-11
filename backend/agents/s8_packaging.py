from __future__ import annotations

import io
import json
import logging
import re
import uuid
import zipfile
from datetime import datetime, timezone

from .base import BaseAgent
from ..core import db
from ..core.models import JobStatus, S8Input, S8Output

logger = logging.getLogger(__name__)


def _slugify(text: str, max_len: int = 40) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"[\s_]+", "-", text).strip("-")
    return text[:max_len] or "polyinsight"


class S8PackagingAgent(BaseAgent[S8Input, S8Output]):
    """S8: PNG bytes + CardData → SQLite 저장 + ZIP 생성. 항상 실행."""

    async def execute(self, input_data: S8Input) -> S8Output:
        job_id = input_data.job_id
        has_error = False

        # ── 1. card_data JSON 저장 ─────────────────────────────────────────────
        try:
            card_json = input_data.card_data.model_dump_json()
            await db.save_card_data(job_id, card_json)
        except Exception as exc:
            logger.error("S8: card_data save failed — %s", exc)
            has_error = True

        # ── 2. PNG bytes 저장 ──────────────────────────────────────────────────
        for i, png in enumerate(input_data.images, start=1):
            try:
                await db.save_card_image(job_id, card_num=i, png_bytes=png)
            except Exception as exc:
                logger.error("S8: card_image %d save failed — %s", i, exc)
                has_error = True

        # ── 3. ZIP 생성 ────────────────────────────────────────────────────────
        zip_bytes: bytes | None = None
        try:
            title_fv = input_data.card_data.card1.title
            slug = _slugify(title_fv.value or "polyinsight")
            month = datetime.now(timezone.utc).strftime("%Y%m")
            zip_name = f"polyinsight_{slug}_{month}.zip"

            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
                for i, png in enumerate(input_data.images, start=1):
                    zf.writestr(f"card_{i:02d}.png", png)
                zf.writestr("card_data.json", input_data.card_data.model_dump_json(indent=2))
            zip_bytes = buf.getvalue()

            export_job_id = str(uuid.uuid4())
            await db.save_export(export_job_id, job_id, zip_bytes, zip_name)
            logger.info("S8: ZIP saved (%d bytes)", len(zip_bytes))
        except Exception as exc:
            logger.error("S8: ZIP creation failed — %s", exc)
            has_error = True

        # ── 4. warnings 저장 + 최종 상태 업데이트 ──────────────────────────────
        final_status = JobStatus.ERROR if has_error else JobStatus.DONE
        if not input_data.images:
            final_status = JobStatus.ERROR

        try:
            await db.update_job(
                job_id,
                status=final_status,
                stage="S8",
                progress=100,
                warnings=input_data.warnings,
            )
        except Exception as exc:
            logger.error("S8: job status update failed — %s", exc)

        logger.info("S8: done. status=%s", final_status)
        return S8Output(job_id=job_id, status=final_status)


s8_agent = S8PackagingAgent()
