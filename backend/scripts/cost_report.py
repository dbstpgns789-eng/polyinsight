# -*- coding: utf-8 -*-
"""LLM 원가 리포트 — 덱 1건의 COGS를 실측으로 뽑는다 (무료, LLM 호출 없음).

두 원장을 대조한다:
  ① Anthropic Console CSV = 실지출(ground truth). 우리 코드가 못 보는 콜(저지·비전·편집)도 포함.
  ② SQLite events(deck_pipeline_complete) = 덱별 토큰 원장. 어떤 덱이 비쌌는지는 여기만 안다.

사용:
  python -m backend.scripts.cost_report --csv "C:/Users/User/Downloads/claude_api_tokens_2026_06.csv" \
                                        --csv "C:/Users/User/Downloads/claude_api_tokens_2026_07.csv"
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

import aiosqlite

from backend.core.config import settings

# $ per 1M tokens (input, output). 캐시 read는 입력의 10%, write는 125%.
PRICES = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}


def _price(model: str) -> tuple[float, float]:
    for k, v in PRICES.items():
        if model.startswith(k):
            return v
    return (3.0, 15.0)   # 알 수 없으면 Sonnet급으로 보수 추정


def _cost(model: str, tin: int, tout: int, cache_read: int = 0, cache_write: int = 0) -> float:
    pin, pout = _price(model)
    return (tin * pin + cache_write * pin * 1.25 + cache_read * pin * 0.1) / 1e6 + tout * pout / 1e6


def csv_report(paths: list[Path]) -> dict:
    """Console CSV = 실지출. 모델별·월별 집계."""
    by_model: dict[str, dict] = defaultdict(lambda: {"tin": 0, "tout": 0, "cr": 0, "cw": 0, "cost": 0.0})
    by_month: dict[str, float] = defaultdict(float)
    for p in paths:
        with p.open(encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                m = row["model_version"]
                tin = int(row["usage_input_tokens_no_cache"] or 0)
                tout = int(row["usage_output_tokens"] or 0)
                cr = int(row["usage_input_tokens_cache_read"] or 0)
                cw = int(row["usage_input_tokens_cache_write_5m"] or 0) + int(
                    row["usage_input_tokens_cache_write_1h"] or 0)
                c = _cost(m, tin, tout, cr, cw)
                d = by_model[m]
                d["tin"] += tin; d["tout"] += tout; d["cr"] += cr; d["cw"] += cw; d["cost"] += c
                by_month[row["usage_date_utc"][:7]] += c
    return {"by_model": dict(by_model), "by_month": dict(by_month)}


async def db_report() -> list[dict]:
    """events = 덱별 토큰 원장."""
    path = settings.DATABASE_URL.replace("sqlite:///", "")
    out: list[dict] = []
    async with aiosqlite.connect(path) as c:
        c.row_factory = aiosqlite.Row
        async with c.execute(
            "SELECT created_at, payload FROM events "
            "WHERE event_type='deck_pipeline_complete' ORDER BY created_at"
        ) as cur:
            for r in await cur.fetchall():
                try:
                    p = json.loads(r["payload"])
                except Exception:
                    continue
                model = p.get("model") or "claude-opus-4-8"
                tin, tout = p.get("input_tokens", 0), p.get("output_tokens", 0)
                if not tin and not tout:
                    continue
                out.append({
                    "at": r["created_at"][:16],
                    "model": model,
                    "tin": tin, "tout": tout,
                    "calls": p.get("llm_calls", 0),
                    "cards": p.get("card_count", 0),
                    "dur": p.get("duration_s", 0),
                    "status": p.get("status"),
                    "cost": _cost(model, tin, tout),
                })
    return out


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", action="append", default=[], type=Path)
    args = ap.parse_args()

    print("=" * 74)
    print("① 실지출 (Anthropic Console CSV — ground truth)")
    print("=" * 74)
    total = 0.0
    if args.csv:
        rep = csv_report(args.csv)
        print(f"{'모델':26} {'입력':>10} {'출력':>9} {'캐시read':>9} {'비용':>8}")
        for m, d in sorted(rep["by_model"].items(), key=lambda x: -x[1]["cost"]):
            print(f"{m:26} {d['tin']:>10,} {d['tout']:>9,} {d['cr']:>9,} ${d['cost']:>7.2f}")
            total += d["cost"]
        print(f"{'':26} {'':>10} {'':>9} {'합계':>9} ${total:>7.2f}")
        print()
        print("월별:", " · ".join(f"{k} ${v:.2f}" for k, v in sorted(rep["by_month"].items())))

    print()
    print("=" * 74)
    print("② 덱별 원장 (SQLite events — 어떤 덱이 비쌌나)")
    print("=" * 74)
    decks = asyncio.run(db_report())
    done = [d for d in decks if d["status"] == "DONE"]
    if not decks:
        print("(기록 없음)")
        return

    costs = [d["cost"] for d in done]
    print(f"덱 시도 {len(decks)}건 · 완료(DONE) {len(done)}건 · 실패/중단 {len(decks)-len(done)}건")
    print()
    print(f"{'시각':17} {'모델':18} {'콜':>2} {'입력':>8} {'출력':>7} {'카드':>4} {'초':>5} {'원가':>7}  상태")
    for d in decks:
        flag = " ⚠재시도" if d["calls"] > 1 else ""
        print(f"{d['at']:17} {d['model'][:18]:18} {d['calls']:>2} {d['tin']:>8,} {d['tout']:>7,} "
              f"{d['cards']:>4} {d['dur']:>5.0f} ${d['cost']:>6.2f}  {d['status']}{flag}")

    if costs:
        print()
        print(f"완료 덱 원가:  평균 ${st.mean(costs):.2f} · 중앙값 ${st.median(costs):.2f} · "
              f"최소 ${min(costs):.2f} · 최대 ${max(costs):.2f}")
        print(f"완료 덱 토큰:  입력 평균 {st.mean([d['tin'] for d in done]):,.0f} · "
              f"출력 평균 {st.mean([d['tout'] for d in done]):,.0f}")
        db_total = sum(d["cost"] for d in decks)
        print(f"DB 원장 합계:  ${db_total:.2f}")
        if total:
            print(f"CSV 실지출:    ${total:.2f}")
            print(f"★차액:         ${total - db_total:.2f}  "
                  f"(= 파이프라인 밖 콜: 저지·비전수정·편집·개발 실험)")
            if done:
                print(f"★실효 단가:    ${total/len(done):.2f}/덱  (총지출 ÷ 완료 덱)")
                print(f"  vs 원장 단가: ${st.mean(costs):.2f}/덱  (저작 콜만)")


if __name__ == "__main__":
    main()
