# -*- coding: utf-8 -*-
"""단일 저작 파이프라인(헌법 v3.0) 테스트 — LLM 없이 mock으로 전 배관 검증."""
from __future__ import annotations

import json
import pathlib
import re

import pytest

from backend.core import db
from backend.core.config import settings
from backend.core.fidelity import verify_deck
from backend.core.models import PaperMetadata
from backend.agents.deck import authoring, deck_renderer, mock
from backend.agents.deck.pipeline import persist_edited_deck, run_authoring_pipeline

_ATTN_PDF = pathlib.Path(
    r"C:\Users\User\Desktop\한국생산기술연구원_근로장학"
    r"\poly_claude_code\논문\golden_22\NIPS-2017-attention-is-all-you-need-Paper.pdf"
)


@pytest.fixture
def mock_llm(monkeypatch):
    monkeypatch.setattr(settings, "DEV_MOCK_LLM", True)


def test_verify_deck_classifies_provenance():
    """해자=정량 수치(단위·소수)만 원문 대조. 맨정수(권/연도/페이지)·CSS는 제외."""
    paper = "The model scored 28.4 BLEU on EN-DE. Trained in 3.5 days. Loading 19.36%."
    html = (
        '<div data-screen-label="01" style="color:oklch(95.5% 0.012 152)">'
        '<h1>28.4 BLEU</h1><p>3.5일</p><p>로딩 19.36 %</p>'
        '<p>수율 99.9 %</p><p>2018 BERT</p><p>Vol. 372 (2026) · 01 / 07</p></div>'
    )
    claims = verify_deck(html, paper)
    by_val = {c.value.strip(): c.verified for c in claims}
    assert by_val.get("28.4") is True       # 소수 → 정량. 'BLEU'의 B를 단위로 오인하지 않음
    assert any(c.verified and c.value.strip().startswith("3.5") for c in claims)  # "3.5일"
    assert by_val.get("19.36 %") is True     # 단위 % → 정량, 원문 존재
    # 지어낸 정량 수치(원문에 없는 99.9%)는 UNVERIFIED로 표면화 — 날조 잡기
    assert by_val.get("99.9 %") is False
    # 맨정수(연도 2018·2026, 권번호 372, 페이지 01/07)는 claim 아님 (서지/네비 노이즈)
    assert not any(re.fullmatch(r"\d+", c.value.strip()) for c in claims)
    # CSS 토큰(95.5/0.012/152)은 검증 대상에서 제외(오탐 없음)
    assert "95.5" not in by_val and "152" not in by_val


def test_mock_deck_html_has_cards():
    html = mock.mock_deck_html(7)
    assert "data-screen-label" in html
    assert html.lstrip().startswith("<!DOCTYPE") or "<html" in html


async def test_author_deck_mock_mode(mock_llm):
    html = await authoring.author_deck(
        raw_text="Attention is all you need. BLEU 28.4.",
        metadata=PaperMetadata(title="Attention", authors=["Vaswani"], year=2017, doi=None),
        card_count=7,
    )
    assert "data-screen-label" in html


def test_strip_code_fence():
    assert authoring._strip_code_fence("```html\n<div>x</div>\n```") == "<div>x</div>"
    assert authoring._strip_code_fence("<div>y</div>") == "<div>y</div>"


def test_prompts_format_without_keyerror():
    """SYSTEM/USER 프롬프트가 리터럴 중괄호 없이 포맷된다(mock이 건너뛰는 배관을 실호출 전 검증).
    P0: 검증배지·용어번역 규칙(SYSTEM)과 publisher 필드(USER) 주입 확인."""
    from backend.agents.deck import authoring_prompts as P
    sys = P.AUTHORING_SYSTEM.format(persona="p")
    assert "왜 브릿지" in sys and "반드시 번역" in sys
    usr = P.AUTHORING_USER.format(
        few_shot_refs="", section_map_text="본문", title="t", authors="a",
        year=2024, card_count=7, art_direction="", publisher="한국생산기술연구원",
    )
    assert "발행 주체" in usr and "한국생산기술연구원" in usr


async def test_render_deck_produces_pngs():
    html = mock.mock_deck_html(7)
    images, warnings = await deck_renderer.render_deck(html, scale=1)
    assert len(images) >= 1
    assert all(png[:8] == b"\x89PNG\r\n\x1a\n" for png in images)  # PNG 시그니처


@pytest.mark.skipif(not _ATTN_PDF.exists(), reason="attention pdf 없음")
async def test_authoring_pipeline_mock_e2e(mock_llm):
    """S1 추출 → 저작(mock) → 검증 → 저장 → 렌더 → 이미지 저장 전 구간."""
    jid = "test-deck-e2e"
    await db.delete_job(jid)
    await db.create_job(jid, title="attention.pdf")
    try:
        await run_authoring_pipeline(jid, _ATTN_PDF.read_bytes(), card_count=7)
        job = await db.get_job(jid)
        deck = await db.get_authored_deck(jid)
        imgs = await db.get_card_images(jid)
        assert job["status"] == "DONE"
        assert deck and "data-screen-label" in deck["html"]
        v = json.loads(deck["verify_json"])
        assert v["verified"] >= 1
        assert len(imgs) >= 1
    finally:
        await db.delete_job(jid)


async def test_deck_db_roundtrip():
    jid = "test-deck-rt2"
    await db.delete_job(jid)
    await db.create_job(jid, title="rt.pdf")
    try:
        await db.save_authored_deck(jid, "<div data-screen-label='01'>x</div>",
                                    json.dumps({"verified": 2, "unverified": 1}), 7)
        got = await db.get_authored_deck(jid)
        assert got["card_count"] == 7
        assert json.loads(got["verify_json"])["verified"] == 2
    finally:
        await db.delete_job(jid)


async def test_paper_text_roundtrip_and_preserve():
    """원문 저장→조회 라운드트립 + 편집 저장(paper_text 생략) 시 원문 보존(COALESCE)."""
    jid = "test-deck-pt"
    await db.delete_job(jid)
    await db.create_job(jid, title="pt.pdf")
    try:
        html = "<div data-screen-label='01'>x</div>"
        await db.save_authored_deck(jid, html, json.dumps({"verified": 1}), 7,
                                    paper_text="ORIGINAL PAPER TEXT")
        got = await db.get_authored_deck(jid)
        assert got["paper_text"] == "ORIGINAL PAPER TEXT"
        # 편집 저장: paper_text 생략 → 기존 원문 보존(덮어쓰지 않음)
        await db.save_authored_deck(jid, html + "<!--edited-->",
                                    json.dumps({"verified": 1}), 7)
        again = await db.get_authored_deck(jid)
        assert again["paper_text"] == "ORIGINAL PAPER TEXT"
    finally:
        await db.delete_job(jid)


async def test_persist_edited_deck_null_fallback_warns():
    """원문 없는 기존 덱 편집 저장 → 재검증 건너뛰되 경고 표면화(막지 않음, 헌법 3조)."""
    jid = "test-deck-nullfb"
    await db.delete_job(jid)
    await db.create_job(jid, title="nf.pdf")
    try:
        deck_html = mock.mock_deck_html(7)
        await db.save_authored_deck(jid, deck_html, json.dumps({"verified": 0}), 7)  # paper_text NULL
        result = await persist_edited_deck(jid, deck_html)
        assert any("재검증 불가" in w for w in result["warnings"])
        assert result["verify"].get("skipped") is True
        assert result["cardCount"] >= 1                      # 막지 않고 렌더는 진행
        imgs = await db.get_card_images(jid)
        assert len(imgs) >= 1
    finally:
        await db.delete_job(jid)


async def test_deck_asset_roundtrip():
    """자산 바이트 저장→조회 라운드트립 + delete_job 정리."""
    jid = "test-asset-rt"
    await db.delete_job(jid)
    await db.create_job(jid, title="a.pdf")
    try:
        png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
        await db.save_deck_asset(jid, "asset-1", png, "image/png",
                                 source_type="upload-owned")
        got = await db.get_deck_asset(jid, "asset-1")
        assert got is not None
        assert got["bytes"] == png
        assert got["mime"] == "image/png"
        assert got["source_type"] == "upload-owned"
        await db.delete_job(jid)
        assert await db.get_deck_asset(jid, "asset-1") is None
    finally:
        await db.delete_job(jid)


async def test_inline_deck_assets_replaces_url():
    """저장 HTML의 자산 URL이 렌더 전처리에서 data URI로 치환된다(auth/base 공백 회피)."""
    from backend.agents.deck.deck_renderer import _inline_deck_assets
    jid = "test-inline"
    await db.delete_job(jid)
    await db.create_job(jid, title="i.pdf")
    try:
        png = b"\x89PNG\r\n\x1a\n" + b"\x01" * 64
        await db.save_deck_asset(jid, "aid9", png, "image/png")
        html = f'<img src="/api/deck/{jid}/assets/aid9">'
        out = await _inline_deck_assets(html, jid)
        assert "/api/deck/" not in out          # URL이 사라짐
        assert "data:image/png;base64," in out  # data URI로 치환
    finally:
        await db.delete_job(jid)


async def test_inserted_image_survives_to_rendered_png():
    """자산 URL을 담은 카드 HTML → persist → 재렌더 PNG가 순수 배경 렌더와 다름.
    (인라인 경로가 실제로 픽셀을 그림 = auth/base/2MB/직렬화 리스크 실증 폐쇄)"""
    jid = "test-rt-pixel"
    await db.delete_job(jid)
    await db.create_job(jid, title="rt.pdf")
    try:
        # 눈에 띄는 단색 이미지(빨강 400x300) — 실제 유효 PNG 필요.
        from PIL import Image
        import io as _io
        buf = _io.BytesIO()
        Image.new("RGB", (400, 300), (220, 40, 40)).save(buf, format="PNG")
        red_png = buf.getvalue()
        await db.save_deck_asset(jid, "redA", red_png, "image/png")

        base_html = (
            '<!DOCTYPE html><html><head><meta charset=utf-8></head><body>'
            '<div data-screen-label="01" style="width:1080px;height:1350px;'
            'position:relative;background:#0A0E1A;box-sizing:border-box"></div>'
            '</body></html>'
        )
        img_html = base_html.replace(
            '</div>',
            f'<img src="/api/deck/{jid}/assets/redA" data-asset-id="redA" '
            f'data-source-type="upload-owned" '
            f'style="position:absolute;left:340px;top:525px;width:400px;height:300px;'
            f'object-fit:cover"></div>',
        )
        # 기존 authored_deck 필요(persist가 조회) — paper_text 없이 저장.
        await db.save_authored_deck(jid, base_html, json.dumps({"verified": 0}), 1)

        # 베이스라인(이미지 없음) 렌더
        base_imgs, _ = await deck_renderer.render_deck(base_html, scale=1, job_id=jid)
        # 삽입본 저장 + 재렌더
        await persist_edited_deck(jid, img_html)
        got = await db.get_card_images(jid)
        assert len(got) >= 1
        assert base_imgs and got[1] != base_imgs[0]     # 픽셀이 달라짐
        # 저장 HTML은 URL 참조 유지(2MB 한도 — base64 저장 금지)
        deck = await db.get_authored_deck(jid)
        assert "/api/deck/" in deck["html"]
        assert "data:image/png;base64," not in deck["html"]
        assert 'data-asset-id="redA"' in deck["html"]   # 메타 직렬화 생존
    finally:
        await db.delete_job(jid)
