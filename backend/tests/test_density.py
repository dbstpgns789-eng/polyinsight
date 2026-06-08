"""S6 발행급 밀도 경고(_density_warnings) — docs/21 A1 슬라이드수·A4 글자수."""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from backend.core.models import CardEditorData, CardMeta, CardSlot, FieldValue
from backend.agents.s6_card_json import S6CardJsonAgent


def _meta() -> CardMeta:
    fv = {"value": "x"}
    return CardMeta.model_validate(
        {"org": fv, "dept": fv, "researcher": fv, "month": fv, "edition_number": fv}
    )


def _card(num: int, headline: str) -> CardSlot:
    return CardSlot(card_num=num, template_type="cover_v2",
                    fields={"headline": FieldValue(value=headline)})


def test_density_flags_long_headline_and_bad_count():
    # 1장(권장 5~7 위반) + headline 40자(상한 30 초과)
    data = CardEditorData(meta=_meta(), cards=[_card(1, "가" * 40)])
    warns = S6CardJsonAgent._density_warnings(data)
    assert any("슬라이드 수" in w for w in warns)
    assert any("headline" in w and "40자" in w for w in warns)


def test_density_excludes_emphasis_markers():
    # 28자 + 별표 4개 = 32자지만, 별표 제외하면 28자 → 상한 30 이내 → 경고 없음
    text = "*" + "가" * 14 + "*" + "*" + "나" * 14 + "*"
    cards = [_card(i, "짧은 제목") for i in range(1, 5)] + [_card(5, text)]
    data = CardEditorData(meta=_meta(), cards=cards)
    warns = S6CardJsonAgent._density_warnings(data)
    assert all("headline" not in w for w in warns)


def test_density_clean_passes():
    cards = [_card(i, "짧은 제목") for i in range(1, 6)]  # 5장, 전부 짧음
    data = CardEditorData(meta=_meta(), cards=cards)
    assert S6CardJsonAgent._density_warnings(data) == []
