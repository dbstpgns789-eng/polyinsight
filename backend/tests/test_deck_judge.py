# -*- coding: utf-8 -*-
"""deck_judge 파서·루프 안전성 단위 테스트 — LLM 호출 없음(무료)."""
import asyncio

import backend.scripts.deck_judge as dj
from backend.scripts.deck_judge import parse_judge_json

_GOOD = ('{"scores": {"hook": 3, "narrative": 4, "accessibility": 3, "integrity": 2, "finish": 4}, '
         '"defects": {"emoji": true, "placeholder": false, "untranslated_unit": true, '
         '"derived_number_suspect": true, "dead_zone": true, "text_visual_mismatch": true}, '
         '"verdict": "pause", "top_problems": ["card6 170%"], "one_line": "조건부"}')


def test_parse_plain_json():
    r = parse_judge_json(_GOOD)
    assert r["scores"]["hook"] == 3
    assert r["defects"]["emoji"] is True
    assert r["verdict"] == "pause"


def test_parse_fenced_json_with_prose():
    raw = "심사 결과입니다.\n```json\n" + _GOOD + "\n```\n이상입니다."
    r = parse_judge_json(raw)
    assert r["scores"]["finish"] == 4


def test_parse_garbage_returns_none():
    assert parse_judge_json("점수를 매길 수 없습니다") is None


def test_parse_diversity_json():
    raw = '{"diversity": 4, "distinct_formats": 5, "similar_pairs": [[1, 3]], "one_line": "ok"}'
    r = parse_judge_json(raw, required=("diversity",))
    assert r["diversity"] == 4
    assert parse_judge_json(_GOOD, required=("diversity",)) is None  # 필수키 분기 동작


def test_judge_dir_survives_repeated_asyncio_run(tmp_path, monkeypatch):
    # eval_runner는 논문마다 asyncio.run을 새로 연다 — 싱글턴 AsyncAnthropic은 첫 루프에
    # 묶여 2번째 호출에서 'Event loop is closed'로 죽는다. 호출당 클라이언트 생성 계약 검증.
    (tmp_path / "card01.png").write_bytes(b"png")

    class _FakeClient:
        async def call(self, **kwargs):
            return ('{"scores": {"hook": 3, "narrative": 3, "accessibility": 3, '
                    '"integrity": 3, "finish": 3}, "defects": {}}')

    monkeypatch.setattr(dj, "LLMClient", lambda: _FakeClient())
    r1 = asyncio.run(dj.judge_dir(tmp_path))
    r2 = asyncio.run(dj.judge_dir(tmp_path))
    assert r1 and r2
