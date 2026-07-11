# -*- coding: utf-8 -*-
"""블랙박스 덱 저지 — 렌더된 카드 PNG를 외부 심사자 루브릭으로 채점 (비전 1콜)
+ 다양성 교차저지(여러 덱 표지 비교 — 동질화 측정).

사용:
  python -m backend.scripts.deck_judge --dir <png폴더> [--out result.json] [--repeat N]

루브릭은 2026-07-11 블랙박스 심사(미세구슬 덱)에서 고정. 프롬프트 변경 시 같은 루브릭·같은
eval셋으로 재채점해 회귀를 측정한다.

★저지는 확률적이다 — claude-sonnet-5는 sampling 파라미터를 받지 않아(llm_client가
  _NO_SAMPLING_PREFIXES로 드롭) 기본 온도로 샘플링된다. temperature=0을 넘겨봐야 no-op다.
  점수 비교는 --repeat로 실측한 노이즈 밴드 기준으로만 한다.
★AsyncAnthropic은 자신을 만든 이벤트 루프에 묶인다 — eval_runner가 asyncio.run을 논문마다
  새로 열므로, 모듈 싱글턴(llm_client) 대신 호출당 LLMClient를 새로 만든다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

from backend.core.config import settings
from backend.core.llm_client import LLMClient

JUDGE_SYSTEM = """너는 이 게시물과 아무 관련 없는 외부 심사자다. 연구기관 공식 인스타그램에
실제로 올라온 카드뉴스라 가정하고 냉정하게 심사한다. 덕담 금지 — 너는 통과시키는 사람이 아니라 거르는 사람이다.

다음 5축을 1~5점으로 채점하라(3=평범한 기관 계정 수준, 5=발행급):
- hook: 표지만 보고 2~3초 안에 손가락이 멈추고 무슨 얘기인지 감이 오는가
- narrative: N장이 하나의 이야기로 이어지는가(뚝뚝 끊기면 감점)
- accessibility: 비전공자가 걸려 넘어지는 지점(외계어·설명 없는 단위·빽빽한 도표)이 없는가
- integrity: 수치가 자기 차트·본문과 모순 없고, 그림이 본문 주장(모양·개수)과 일치하는가
- finish: 마감 완성도(공백 붕괴·요소 겹침·톤 불일치 없이 발행 가능한가)

다음 결함을 이진 판정하라(true=결함 존재):
- emoji: 이모지 문자가 아이콘으로 쓰임
- placeholder: 미치환 자리표시자([기관명] 등)
- untranslated_unit: 첫 등장에 쉬운 앵커 없는 전문 단위·약어(wt%·무설명 약자 등)
- derived_number_suspect: 증가율·배수가 카드 안 다른 숫자와 산수가 안 맞음
- dead_zone: 카드 세로 1/3 이상이 통째로 빈 카드가 있음
- text_visual_mismatch: 본문이 말한 형상과 다른 그림

마지막으로 verdict: "skip"(안 올림) | "pause"(고치면 올림) | "save"(그대로 올림).

출력은 아래 JSON 하나만(코드펜스·설명 없이):
{"scores": {"hook": n, "narrative": n, "accessibility": n, "integrity": n, "finish": n},
 "defects": {"emoji": b, "placeholder": b, "untranslated_unit": b, "derived_number_suspect": b, "dead_zone": b, "text_visual_mismatch": b},
 "verdict": "...", "top_problems": ["카드번호 짚어 최대 3개"], "one_line": "한 줄 총평"}"""

DIVERSITY_SYSTEM = """너는 한 연구기관 인스타그램 계정의 피드를 보고 있다. 첨부된 N장은 이 계정이
서로 다른 논문으로 발행한 게시물들의 '표지'다. '같은 도구로 찍어낸 티'가 나는지 심사하라:
- 각 표지의 팔레트·레이아웃 골격·서사 유형을 짧게 분류하고
- 같은 템플릿으로 보이는 쌍을 지목하라(첨부 순서 번호, 1부터)
- diversity: 1(전부 같은 템플릿) ~ 5(계정답게 다양하면서 브랜드는 유지)

출력은 아래 JSON 하나만(코드펜스·설명 없이):
{"diversity": n, "distinct_formats": n, "similar_pairs": [[1, 3]], "one_line": "한 줄 총평"}"""

_JSON_RE = re.compile(r"\{.*\}", re.S)


def parse_judge_json(raw: str, required: tuple[str, ...] = ("scores", "defects")) -> dict | None:
    """저지 응답에서 JSON 하나를 강건하게 추출. 필수키 없으면 None."""
    m = _JSON_RE.search(raw)
    if not m:
        return None
    try:
        obj = json.loads(m.group())
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or not all(k in obj for k in required):
        return None
    return obj


async def judge_dir(png_dir: Path) -> dict | None:
    """카드 PNG 폴더(정렬순) → 저지 결과 dict."""
    pngs = sorted(png_dir.glob("*.png"))
    if not pngs:
        raise SystemExit(f"[ERROR] PNG 없음: {png_dir}")
    images = [p.read_bytes() for p in pngs]
    client = LLMClient()   # 호출당 생성 — asyncio.run 반복(eval_runner) 안전
    raw = await client.call(
        system_prompt=JUDGE_SYSTEM,
        user_prompt=f"카드 {len(images)}장이 게시물 전부다(첨부 순서=게재 순서). 심사하라.",
        model=settings.LLM_MODEL_JUDGE,
        max_tokens=settings.JUDGE_MAX_TOKENS,
        timeout_s=180,
        images=images,
    )
    return parse_judge_json(raw)


async def judge_diversity(cover_pngs: list[bytes], labels: list[str]) -> dict | None:
    """여러 덱의 표지 교차 비교 — 동질화 점수 (비전 1콜). labels는 첨부 순서와 1:1."""
    client = LLMClient()
    raw = await client.call(
        system_prompt=DIVERSITY_SYSTEM,
        user_prompt=f"표지 {len(cover_pngs)}장, 첨부 순서대로: "
                    + ", ".join(f"{i + 1}={lab}" for i, lab in enumerate(labels)),
        model=settings.LLM_MODEL_JUDGE,
        max_tokens=1000,
        timeout_s=120,
        images=cover_pngs,
    )
    return parse_judge_json(raw, required=("diversity",))


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")   # Windows cp949 콘솔 방어
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="덱 블랙박스 저지 (유료 — 비전 1콜)")
    ap.add_argument("--dir", required=True, help="카드 PNG 폴더")
    ap.add_argument("--out", default=None, help="결과 JSON 저장 경로(생략 시 stdout)")
    ap.add_argument("--repeat", type=int, default=1, help="반복 채점(저지 노이즈 밴드 측정용)")
    args = ap.parse_args()

    runs = [asyncio.run(judge_dir(Path(args.dir))) for _ in range(args.repeat)]
    if not any(runs):
        print("[ERROR] 저지 응답 파싱 실패", file=sys.stderr)
        sys.exit(1)
    result = runs[0] if args.repeat == 1 else {"runs": runs}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"저장: {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
