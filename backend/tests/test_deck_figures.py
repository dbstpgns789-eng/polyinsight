# -*- coding: utf-8 -*-
"""논문 figure 추출 — '논문이 곧 레퍼런스'(D안)의 입력.

남의 덱(refs)이 아니라 이 논문이 스스로 입고 있는 옷(SEM·그래프·도식)을 모델에 보여준다.
앵커가 논문 자신이면 동질화는 원리적으로 불가능하다 — 논문마다 그림이 다르므로.
"""
import pathlib

import pytest

from backend.agents.deck.figures import extract_figures

_PAPERS = pathlib.Path(r"C:\Users\User\Desktop\한국생산기술연구원_근로장학\poly_claude_code\논문")
_MICROBEAD = _PAPERS / "80 [cellulose_2024] Fabrication of composite microbeads consisting of cellulose and covalent organic nanosheets via electrospray process (1) (2).pdf"
_ATTENTION = _PAPERS / "1706.03762v7.pdf"


def test_no_pdf_returns_empty():
    """빈 입력·깨진 PDF는 조용히 빈 리스트 — figure가 없다고 저작이 멈추면 안 된다(소프트)."""
    assert extract_figures(b"") == []
    assert extract_figures(b"not a pdf at all") == []


@pytest.mark.skipif(not _MICROBEAD.exists(), reason="microbead pdf 없음")
def test_extracts_figures_from_real_paper():
    figs = extract_figures(_MICROBEAD.read_bytes(), max_figures=3)
    assert 1 <= len(figs) <= 3
    assert all(f[:8] == b"\x89PNG\r\n\x1a\n" for f in figs)   # PNG 시그니처
    assert all(len(f) < 4_000_000 for f in figs)              # 이미지당 API 한계(5MB) 아래


@pytest.mark.skipif(not _MICROBEAD.exists(), reason="microbead pdf 없음")
def test_spreads_across_pages_when_candidates_allow():
    """후보가 충분하면 페이지를 분산해 고른다 — 논문의 시각 '범위'를 보여주기 위해.

    (같은 페이지의 큰 패널만 뽑으면 그 논문이 한 종류의 그림으로만 보인다. 앞쪽 도식 ·
     중간 사진 · 뒤쪽 그래프가 섞여야 팔레트의 축이 하나로 수렴하지 않는다.)
    후보가 적은 논문(attention: 3장, 그중 2장이 같은 페이지)은 분산이 불가능하므로 강제하지 않는다.
    """
    figs = extract_figures(_MICROBEAD.read_bytes(), max_figures=3, _return_meta=True)
    pages = [m["page"] for m in figs]
    assert len(set(pages)) == len(pages), f"같은 페이지에서 중복 추출: {pages}"
    assert pages == sorted(pages), "논문 흐름 순서로 정렬돼야 한다"


@pytest.mark.skipif(not _ATTENTION.exists(), reason="attention pdf 없음")
def test_few_candidates_still_returns_figures():
    """후보가 적은 논문도 빈손으로 돌려보내지 않는다(분산은 best-effort)."""
    figs = extract_figures(_ATTENTION.read_bytes(), max_figures=3)
    assert len(figs) >= 2
