from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.scripts.input_profile import journal_family_from_doi


def test_known_publishers():
    assert journal_family_from_doi("10.1016/j.carbpol.2024.01") == "Elsevier"
    assert journal_family_from_doi("10.1002/anie.202012345") == "Wiley"
    assert journal_family_from_doi("10.1038/s41586-024-00001") == "Nature"


def test_none_or_garbage_is_unknown():
    assert journal_family_from_doi(None) == "unknown"
    assert journal_family_from_doi("") == "unknown"
    assert journal_family_from_doi("not-a-doi") == "unknown"


def test_unknown_prefix_keeps_prefix():
    assert journal_family_from_doi("10.9999/x.y").startswith("other:10.9999")


from backend.scripts.input_profile import columns_from_centers, build_input_profile


def test_columns_single_when_centered():
    centers = [0.5, 0.48, 0.52, 0.45, 0.55] * 20   # 모두 중앙 → 1단
    assert columns_from_centers(centers) == 1


def test_columns_two_when_bimodal_with_gutter():
    left = [0.2, 0.25, 0.3] * 20
    right = [0.7, 0.75, 0.8] * 20                   # 양쪽 차고 중앙 빔 → 2단
    assert columns_from_centers(left + right) == 2


def test_columns_one_when_empty():
    assert columns_from_centers([]) == 1


def test_build_input_profile_merges_columns_and_journal(monkeypatch):
    import backend.scripts.input_profile as ip
    monkeypatch.setattr(ip, "detect_columns", lambda pdf_bytes: 2)
    prof = ip.build_input_profile(b"%PDF-fake", "10.1016/j.x")
    assert prof == {"columns": 2, "journal_family": "Elsevier"}


def test_columns_two_when_bimodal_with_central_noise():
    # 실제 2단 논문: 제목/초록이 full-width라 중앙 단어 비율이 30%까지 올라감.
    # 이전 _GUTTER_MAX=0.10에서는 실패했던 케이스.
    left  = [0.22, 0.27, 0.32] * 30   # 좌측 컬럼 본문
    right = [0.68, 0.73, 0.78] * 30   # 우측 컬럼 본문
    central_noise = [0.48, 0.50, 0.52] * 20  # 제목/초록 full-width (~22%)
    assert columns_from_centers(left + right + central_noise) == 2


from backend.scripts.input_profile import doi_from_text


def test_doi_from_text_finds_bare_doi(tmp_path):
    # pdfplumber가 읽을 수 없는 가짜 bytes — 텍스트 추출 실패 시 None 반환해야 함.
    assert doi_from_text(b"not-a-pdf") is None


def test_build_input_profile_falls_back_to_text_doi(monkeypatch):
    import backend.scripts.input_profile as ip
    monkeypatch.setattr(ip, "detect_columns", lambda pdf_bytes: 1)
    monkeypatch.setattr(ip, "doi_from_text", lambda pdf_bytes: "10.1038/s41586-001")
    prof = ip.build_input_profile(b"%PDF-fake", None)  # doi=None → 텍스트 폴백
    assert prof["journal_family"] == "Nature"
