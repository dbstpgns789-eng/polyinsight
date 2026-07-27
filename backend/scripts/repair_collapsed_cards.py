# -*- coding: utf-8 -*-
"""폭이 붕괴한 카드 탐지·복구 — 2026-07-26.

무엇을 고치나: 편집 진입 시 숨겨진 카드가 freeze되어 모든 요소에 width:0px/height:0px가
박힌 덱. 그 카드는 한글이 한 글자씩 세로로 흐른다. 근본 원인은 editorAgent.freezeCard에
"렌더되지 않은 카드는 freeze하지 않는다" 가드로 수정됐고(커밋 511794d), 이 스크립트는
그 전에 이미 저장돼버린 덱을 되돌린다.

복구 규칙(실측으로 확정):
  freeze는 hidden 카드에서 rect를 전부 0으로 읽어 두 종류의 손상을 남긴다.
    · promoteAll이 승격한 요소 → position:absolute + left:0px + top:0px + margin:0 + w/h:0
      => 인라인을 전부 걷어 원래 CSS 흐름으로 되돌린다.
    · pinCollapsingContainers가 고정한 조상(원래부터 absolute) → w/h만 0
      => w/h만 걷는다. position/left/top은 원본이므로 건드리면 레이아웃이 어긋난다.
  이 구분을 안 하면 상단 크롬이 겹친다(실측 확인).

DOM 조작은 정규식이 아니라 실제 브라우저로 한다 — 인라인 style 파싱을 문자열로 하면 틀린다.

실행 (레포 루트에서):
    .venv/Scripts/python.exe backend/scripts/repair_collapsed_cards.py            # dry-run
    .venv/Scripts/python.exe backend/scripts/repair_collapsed_cards.py --apply    # 실제 저장
--apply는 저장 전에 현재 판을 deck_revision(source='pre_repair')로 남긴다.
"""
from __future__ import annotations

import argparse
import asyncio
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from backend.core import db  # noqa: E402

ZERO_W = re.compile(r"width:\s*0px", re.I)
CARD_SPLIT = re.compile(r"(?=<div[^>]+data-screen-label=)", re.I)

REPAIR_JS = """() => {
  var promoted = 0, pinned = 0, cards = 0;
  document.querySelectorAll('[data-screen-label]').forEach(function (card) {
    var damaged = false;
    card.querySelectorAll('*').forEach(function (el) {
      var s = el.style;
      if (s.width !== '0px' || s.height !== '0px') return;
      damaged = true;
      s.removeProperty('box-sizing'); s.removeProperty('width'); s.removeProperty('height');
      if (s.position === 'absolute' && s.left === '0px' && s.top === '0px') {
        s.removeProperty('margin'); s.removeProperty('position');
        s.removeProperty('left'); s.removeProperty('top');
        promoted++;
      } else {
        pinned++;   // 원래 absolute였던 컨테이너 — 위치는 원본이라 남긴다
      }
    });
    if (damaged) { card.removeAttribute('data-pi-frozen'); cards++; }
  });
  return { promoted: promoted, pinned: pinned, cards: cards,
           html: '<!DOCTYPE html>\\n' + document.documentElement.outerHTML };
}"""


def damaged_cards(html: str) -> int:
    return sum(1 for c in CARD_SPLIT.split(html) if "data-screen-label" in c and ZERO_W.search(c))


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="실제로 저장한다(기본은 dry-run)")
    args = ap.parse_args()

    from playwright.async_api import async_playwright

    async with db._connect() as conn:
        async with conn.execute(
            "SELECT job_id, html FROM authored_deck WHERE html IS NOT NULL"
        ) as cur:
            rows = await cur.fetchall()
    targets = [(jid, html) for jid, html in rows if damaged_cards(html)]
    print(f"덱 {len(rows)}개 스캔 → 손상 {len(targets)}개")
    if not targets:
        return 0

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        for jid, html in targets:
            before = damaged_cards(html)
            await page.set_content(html, wait_until="domcontentloaded")
            r = await page.evaluate(REPAIR_JS)
            after = damaged_cards(r["html"])
            print(f"  {jid}: 손상카드 {before}장 → {after}장 "
                  f"(흐름복귀 {r['promoted']} · 박스만해제 {r['pinned']})")
            if after:
                print("    ⚠ 남은 손상이 있어 저장하지 않는다 — 수동 확인 필요")
                continue
            if args.apply:
                deck = await db.get_authored_deck(jid)
                await db.save_deck_revision(
                    jid, html, deck.get("verify_json") or "[]",
                    deck.get("card_count") or 0, "pre_repair")
                await db.save_authored_deck(
                    jid, r["html"], deck.get("verify_json") or "[]",
                    deck.get("card_count") or 0)
                print("    저장 완료(복구 전 판을 pre_repair로 보관)")
        await browser.close()

    if not args.apply:
        print("\ndry-run 이었다. 실제로 고치려면 --apply 를 붙여라.")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
