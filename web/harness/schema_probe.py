# -*- coding: utf-8 -*-
"""덱 HTML을 JSON 씬그래프로 역산해 비용을 실측한다.

배경: 2026-07-26 "HTML 버리고 Canva/Gamma식 JSON 씬그래프로 가라"는 제안을 판정하려고
      만들었다. 결정 기록은 docs/decisions/2026-07-26-json-scenegraph-vs-html.md.

각 리프 노드를 씬그래프 노드로 직렬화(id/type/text/x/y/w/h + 기본값 아닌 스타일 선언)
한 뒤 JSON 바이트를 재서 원본 HTML 바이트와 비교한다.

최초 측정값(회귀 비교 기준):
  클로드디자인 셀룰로스 9장 : HTML 73,983B / JSON 221,897B (3.00배) / 노드 313 / flow 269·abs 44
  우리 test1 덱      7장 : HTML 37,141B / JSON  58,337B (1.57배) / 노드  87 / flow  20·abs 67
  → JSON은 가볍지 않다. CSS 캐스케이드로 공유되던 선언(6,113개)이 노드마다 펼쳐진다.

TARGETS의 경로를 바꿔 다른 덱에도 돌릴 수 있다.
"""
import json
import pathlib
from playwright.sync_api import sync_playwright

PROBE = r"""
() => {
  const cards = Array.from(document.querySelectorAll(SEL));
  const STRUCT = 'div,section,svg,img,ul,ol,table,figure,canvas,header,footer,article'.split(',');
  const probe = document.createElement('div');
  document.body.appendChild(probe);
  const BASE = {}; const bcs = getComputedStyle(probe);
  for (const p of bcs) BASE[p] = bcs.getPropertyValue(p);
  probe.remove();
  // 논리속성 중복 제거(브라우저 자동생성) + 비시각 속성 제외
  const SKIP = /^(-webkit|-moz|border-(block|inline)|inset-(block|inline)|margin-(block|inline)|padding-(block|inline)|(min|max)-(block|inline)-size|overflow-(block|inline)|caret-color|text-emphasis-color|text-decoration-color|outline-color|column-rule-color|unicode-bidi|overflow-clip-margin|text-wrap-(mode|style)|perspective-origin|transform-origin)/;

  function isTextLeaf(el) {
    for (const s of STRUCT) if (el.querySelector(':scope > ' + s)) return false;
    return (el.textContent || '').trim().length > 0;
  }
  function paints(el) {
    const cs = getComputedStyle(el);
    if (cs.opacity === '0' || cs.visibility === 'hidden') return false;
    return cs.backgroundColor !== 'rgba(0, 0, 0, 0)' || cs.backgroundImage !== 'none'
      || cs.borderStyle !== 'none' || cs.boxShadow !== 'none';
  }

  const pages = [];
  let nodeSeq = 0;
  for (const card of cards) {
    const cr = card.getBoundingClientRect();
    const nodes = [];
    function visit(el) {
      for (const c of Array.from(el.children)) {
        const tag = c.tagName.toLowerCase();
        if (tag === 'br') continue;
        let kind = null, extra = {};
        if (tag === 'svg') { kind = 'graphic'; extra.raw = c.outerHTML; }
        else if (tag === 'img') { kind = 'image'; extra.src = c.getAttribute('src') || ''; }
        else if (isTextLeaf(c)) { kind = 'text'; extra.text = (c.textContent || '').trim(); }
        else if (c.childElementCount === 0) {
          const r0 = c.getBoundingClientRect();
          if (r0.width > 4 && r0.height > 4 && paints(c)) kind = 'shape'; else continue;
        } else { visit(c); continue; }

        const cs = getComputedStyle(c), r = c.getBoundingClientRect();
        const style = {};
        for (const p of cs) {
          if (SKIP.test(p)) continue;
          const v = cs.getPropertyValue(p);
          if (v && v !== BASE[p]) style[p] = v;
        }
        const n = Object.assign({
          id: 'n' + (++nodeSeq), type: kind,
          x: Math.round(r.left - cr.left), y: Math.round(r.top - cr.top),
          width: Math.round(r.width), height: Math.round(r.height),
          style: style
        }, extra);
        nodes.push(n);
      }
    }
    visit(card);
    pages.push({ backgroundColor: getComputedStyle(card).backgroundColor, nodes: nodes });
  }
  return pages;
}
"""

TARGETS = [
    ("클로드디자인", r"C:\Users\User\AppData\Local\Temp\셀룰로스 마이크로비드 카드뉴스 (standalone).html",
     'div[style*="width:1080px"]'),
    ("우리(PolyInsight)", r"C:\Users\User\Desktop\test1_deck_90aa2b86.html", ".card"),
]

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1200, "height": 1500})
    for tag, path, sel in TARGETS:
        page.goto(pathlib.Path(path).as_uri())
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(1200)
        pages = page.evaluate(PROBE.replace("SEL", json.dumps(sel)))

        doc = {"documentId": "doc", "pages": pages}
        js_full = json.dumps(doc, ensure_ascii=False, separators=(",", ":"))
        # SVG raw 없이(=조언자 스키마 그대로, 형태 발명 포기 버전)
        stripped = json.loads(js_full)
        svg_bytes = 0
        for pg in stripped["pages"]:
            for n in pg["nodes"]:
                if "raw" in n:
                    svg_bytes += len(n["raw"].encode("utf-8"))
                    n.pop("raw")
        js_norawsvg = json.dumps(stripped, ensure_ascii=False, separators=(",", ":"))
        # 스타일까지 뺀 최소 스키마 (조언자 예시: type/text/x/y/fontSize)
        minimal = json.loads(js_norawsvg)
        for pg in minimal["pages"]:
            for n in pg["nodes"]:
                st = n.pop("style", {})
                if "font-size" in st:
                    n["fontSize"] = st["font-size"]
        js_min = json.dumps(minimal, ensure_ascii=False, separators=(",", ":"))

        html_bytes = pathlib.Path(path).stat().st_size
        n_nodes = sum(len(pg["nodes"]) for pg in pages)
        decls = sum(len(n.get("style", {})) for pg in pages for n in pg["nodes"])
        print(f"\n=== {tag} ===")
        print(f"원본 HTML          : {html_bytes:>7,} B")
        print(f"씬그래프 JSON(완전): {len(js_full.encode('utf-8')):>7,} B  "
              f"({len(js_full.encode('utf-8'))/html_bytes:.2f}x)")
        print(f"  SVG raw 제외     : {len(js_norawsvg.encode('utf-8')):>7,} B  "
              f"({len(js_norawsvg.encode('utf-8'))/html_bytes:.2f}x)   [SVG {svg_bytes:,}B 손실]")
        print(f"  스타일까지 제외  : {len(js_min.encode('utf-8')):>7,} B  "
              f"({len(js_min.encode('utf-8'))/html_bytes:.2f}x)   [조언자 예시 스키마]")
        print(f"노드 {n_nodes}개 / 스타일 선언 총 {decls}개 (노드당 평균 {decls/n_nodes:.1f})")
    browser.close()
