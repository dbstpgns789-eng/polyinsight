# -*- coding: utf-8 -*-
"""카드 단위 교체 — 비전 수정의 출력을 1/5로 줄인다.

원가 실측(2026-07-13): 비전 루프가 매 라운드 **HTML 전문(15~18k 토큰)을 재출력**한다.
출력 단가는 입력의 5배($25 vs $5) → 라운드당 $0.45, 2라운드 $0.90. **저작($0.51)보다 비싸다.**

'중첩 div라 오려붙이면 깨진다'는 내 판단은 틀렸다 — 실제 덱으로 검증하니 무손실 분해된다.
고친 카드만 받아 교체하면 출력이 15k → 3k로 줄어든다(덱당 $0.60 절감, 원가의 31%).
"""
from backend.agents.deck.card_patch import apply_card_patch, split_cards

_HTML = (
    '<!DOCTYPE html><html><head><style>.x{}</style></head><body>\n'
    '<div data-screen-label="01" style="width:1080px"><p>A</p><div><span>중첩</span></div></div>\n'
    '<div data-screen-label="02" style="width:1080px"><p>B</p></div>\n'
    '<div data-screen-label="03" style="width:1080px"><p>C</p></div>\n'
    '</body></html>'
)


def test_split_is_lossless():
    """분해 → 재조립이 원본과 완전 일치해야 교체가 안전하다."""
    head, cards, tail = split_cards(_HTML)
    assert [lab for lab, _, _ in cards] == ["01", "02", "03"]
    assert head + "".join(div + sep for _, div, sep in cards) + tail == _HTML


def test_identical_patch_yields_identical_html():
    """같은 내용으로 교체하면 원본과 **바이트 단위로 일치**해야 한다.

    (구분자를 카드에 붙여두면 새 카드엔 그게 없어 개행이 사라진다 — 실제 덱에서 잡힌 버그.)
    """
    _, cards, _ = split_cards(_HTML)
    lab, div, _ = cards[1]
    out, n, _ = apply_card_patch(_HTML, div)
    assert n == 1
    assert out == _HTML


def test_patch_replaces_only_given_cards():
    fixed = '<div data-screen-label="02" style="width:1080px"><p>B-fixed</p></div>'
    out, n, warns = apply_card_patch(_HTML, fixed)
    assert n == 1
    assert "B-fixed" in out
    assert "<p>A</p>" in out and "<p>C</p>" in out    # 손 안 댄 카드는 그대로
    assert out.startswith("<!DOCTYPE html>") and out.rstrip().endswith("</html>")
    assert warns == []


def test_patch_preserves_tail_when_last_card_replaced():
    """마지막 카드를 갈아끼워도 </body></html> 꼬리가 살아야 한다."""
    fixed = '<div data-screen-label="03"><p>C2</p></div>'
    out, n, _ = apply_card_patch(_HTML, fixed)
    assert n == 1
    assert "C2" in out
    assert out.rstrip().endswith("</body></html>") or out.rstrip().endswith("</html>")


def test_patch_multiple_cards():
    fixed = ('<div data-screen-label="01"><p>A2</p></div>\n'
             '<div data-screen-label="03"><p>C2</p></div>')
    out, n, _ = apply_card_patch(_HTML, fixed)
    assert n == 2
    assert "A2" in out and "C2" in out and "<p>B</p>" in out


def test_unknown_label_is_ignored():
    """원본에 없는 라벨은 무시 — 모델이 카드를 새로 만들면 안 된다."""
    fixed = '<div data-screen-label="09"><p>유령</p></div>'
    out, n, warns = apply_card_patch(_HTML, fixed)
    assert n == 0
    assert "유령" not in out
    assert any("09" in w for w in warns)


def test_no_changes_marker_returns_original():
    out, n, _ = apply_card_patch(_HTML, "NO_CHANGES")
    assert out == _HTML
    assert n == 0


def test_garbage_returns_original():
    out, n, warns = apply_card_patch(_HTML, "죄송합니다 수정할 수 없습니다")
    assert out == _HTML
    assert n == 0
