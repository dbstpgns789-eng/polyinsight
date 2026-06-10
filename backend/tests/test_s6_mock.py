"""분할 mock (mock_storyboard/mock_cards) (Task 8)."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.agents.s6.mock import mock_storyboard, mock_cards
from backend.core.models import ArchitectOutput, MismatchSignal, PaperMetadata, WriterOutput


def _meta():
    return PaperMetadata(title="셀룰로스 미세구슬", authors=["이호익"], year=2024, doi=None)


def test_mock_storyboard_arc_and_bounds():
    out = mock_storyboard(5, _meta())
    assert isinstance(out, ArchitectOutput)
    beats = out.storyboard.beats
    assert len(beats) == 5
    assert beats[0].template_type == "cover_v2"
    assert beats[-1].template_type == "closing_v2"
    assert all(b.content_shape_reason for b in beats)


def test_mock_cards_align_to_storyboard():
    sb = mock_storyboard(5, _meta()).storyboard
    wr = mock_cards(sb, _meta())
    assert isinstance(wr, WriterOutput)
    assert [c.card_num for c in wr.cards] == [b.card_num for b in sb.beats]
    assert [c.template_type for c in wr.cards] == [b.template_type for b in sb.beats]
    assert wr.mismatch_signals == []


def test_mock_cards_inject_mismatch_and_only_beats():
    sb = mock_storyboard(5, _meta()).storyboard
    sig = [MismatchSignal(card_num=3, reason="x", suggested_shape="multistat")]
    wr = mock_cards(sb, _meta(), inject_mismatch=sig, only_beats=[3])
    assert [c.card_num for c in wr.cards] == [3]          # 부분만
    assert len(wr.mismatch_signals) == 1
    assert wr.mismatch_signals[0].card_num == 3
