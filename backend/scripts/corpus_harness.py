"""코퍼스 견고성 하니스 — Mode A(무료 S1 측정).
폴더의 모든 PDF를 S1만 돌려 degrade 텔레메트리를 input_profile로 교차집계한다.
프로세스 격리 Pool(maxtasksperchild)로 fitz C-메모리 OOM 회피(spec §3).
오프라인 개발 도구 — 웹/프로덕션과 무관."""
from __future__ import annotations

import asyncio
from pathlib import Path

from backend.agents.s1_extractor import s1_agent
from backend.core.models import S1Input
from backend.scripts.input_profile import build_input_profile


def profile_one(pdf_path: str) -> dict:
    """논문 1편 → 직렬화 가능 row(Pool 전송 위해 enum 아닌 str). 워커 진입점."""
    pdf_bytes = Path(pdf_path).read_bytes()
    s1 = asyncio.run(s1_agent.execute(S1Input(job_id=pdf_path, pdf_bytes=pdf_bytes)))
    profile = build_input_profile(pdf_bytes, s1.metadata.doi)
    return {
        "file": Path(pdf_path).name,
        "codes": [e.code.value for e in s1.degrade_events],
        "columns": profile["columns"],
        "journal_family": profile["journal_family"],
    }
