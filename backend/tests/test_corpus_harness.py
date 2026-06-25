from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

import backend.scripts.corpus_harness as harness


def test_profile_one_returns_serializable_row(monkeypatch, tmp_path):
    # S1·input_profile을 가짜로 — 워커 오케스트레이션(파일읽기→실행→직렬화)만 검증.
    from backend.core.models import DegradeCode, DegradeEvent, PaperMetadata, S1Output

    fake_s1 = S1Output(
        raw_text="x", page_map={1: "x"},
        metadata=PaperMetadata(title=None, authors=[], year=None, doi="10.1016/j.x"),
        word_count=5000, degraded=True,
        degrade_events=[DegradeEvent(code=DegradeCode.S1_NO_SECTIONS)],
    )

    async def fake_execute(inp):
        return fake_s1

    monkeypatch.setattr(harness.s1_agent, "execute", fake_execute)
    monkeypatch.setattr(harness, "build_input_profile",
                        lambda pdf_bytes, doi: {"columns": 2, "journal_family": "Elsevier"})

    pdf = tmp_path / "paper_a.pdf"
    pdf.write_bytes(b"%PDF-fake")
    row = harness.profile_one(str(pdf))

    assert row == {
        "file": "paper_a.pdf",
        "codes": ["s1_no_sections"],
        "columns": 2,
        "journal_family": "Elsevier",
    }
    # 직렬화 가능(enum 아님 — Pool 전송 안전)
    import json
    json.dumps(row)
