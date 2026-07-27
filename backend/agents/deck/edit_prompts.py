# -*- coding: utf-8 -*-
"""AI 디자이너 편집 프롬프트 — 전체 HTML 재출력이 아니라 '최소 편집 스펙(ops)' JSON을 요구한다.

정본 정의 docs/contracts/25 + 스펙 2026-07-24-ai-designer-edit-spec.md.
LLM 입력=요소 인벤토리(작음), 출력=ops(작음). 덱 전체를 다시 뽑던 구조(느림·비쌈·타임아웃) 폐기.
"""
from __future__ import annotations

import json

EDIT_SYSTEM = """당신은 완성된 인스타그램 카드뉴스 '덱'을 사용자의 자연어 지시대로 다듬는 **디자이너**입니다.
사용자는 디자인(CSS·색·간격)을 직접 다룰 줄 모릅니다. "고급스럽게", "따뜻하게", "제목 강조" 같은
느낌·의도를 받아, 그걸 **실제 편집 스펙(ops)**으로 번역하는 것이 당신의 일입니다.

★덱을 다시 쓰지 않습니다. 전체 HTML을 출력하지 않습니다. 아래 JSON만 출력합니다.

[출력 계약 — JSON만]
{"summary": "<사용자에게 보여줄 한 줄 요약>", "ops": [ <op>, ... ]}

op은 style 또는 text 두 종류:
  {"eid": "<대상 data-eid>", "op": "style", "style": {"<css-속성>": "<값>"}}
  {"eid": "<대상 data-eid>", "op": "text",  "text": "<새 텍스트>"}

규칙:
- eid는 아래 '요소 목록'에 있는 것만 쓴다. 목록에 없는 eid는 절대 만들지 않는다.
- style 속성명은 kebab-case CSS. 허용: color, background, font-size, font-weight, font-family,
  text-align, text-shadow, letter-spacing, line-height, opacity, border-radius,
  margin(-*), padding(-*), text-decoration, text-transform.
  ✗ 레이아웃 구조(position, display, width, height, transform, float)는 쓰지 않는다(별도 도구 담당).
- 지시에 맞는 요소만 골라 **최소로** 손댄다. 관련 없는 요소는 건드리지 않는다.
- 바꿀 게 없거나 지시가 모호하면 ops를 빈 배열([])로 두고 summary로 이유를 설명한다.
- "더 어둡게/밝게/크게" 같은 상대 지시는 목록의 '현재 스타일'을 기준으로 판단한다.

[충실성 — 해자]
원문에 없는 수치·사실을 새로 만들지 않는다. text는 기존 표현을 다듬되 수치·사실 왜곡 금지.

코드펜스(```)·설명문 없이 **JSON만** 출력한다."""


def _inventory_block(inventory: list[dict]) -> str:
    lines = []
    for it in inventory or []:
        eid = it.get("eid", "")
        kind = it.get("kind", "")
        label = (it.get("label") or "").replace("\n", " ")[:60]
        st = it.get("styles") or {}
        style_hint = " ".join(
            f"{k}={v}" for k, v in st.items()
            if k in ("color", "fontSize", "fontWeight", "background", "textShadow", "textAlign") and v
        )
        lines.append(f'- eid="{eid}" [{kind}] "{label}"' + (f"  ({style_hint})" if style_hint else ""))
    return "\n".join(lines) if lines else "(요소 없음)"


_USER_TMPL = """## 편집 대상 요소 목록 (이 eid만 사용)
{inventory}
{target_block}
## 사용자 지시
{instruction}
{paper_block}
위 지시를 반영하는 편집 스펙(JSON)만 출력하라. 관련 요소만 최소로."""


def build_user_prompt(
    inventory: list[dict], instruction: str, paper_text: str | None, *,
    target: dict | None = None, paper_cap: int = 8000,
) -> str:
    target_block = ""
    if target and target.get("eid"):
        target_block = f'\n## 사용자가 지정한 대상\n- eid="{target["eid"]}" (이 요소 위주로)\n'
    paper_block = ""
    if paper_text:
        paper_block = f"\n## (참고) 원문 — 수치 판단 근거\n{paper_text[:paper_cap]}\n"
    return _USER_TMPL.format(
        inventory=_inventory_block(inventory),
        target_block=target_block,
        instruction=instruction.strip(),
        paper_block=paper_block,
    )


def mock_ops(instruction: str, html: str) -> str:
    """DEV_MOCK_LLM용 — html의 첫 data-eid에 그림자 style op(적용 카운트/배관 검증, 무비용)."""
    import re
    m = re.search(r'data-eid="([^"]+)"', html or "")
    if not m:
        return json.dumps({"summary": "대상 요소가 없어요", "ops": []}, ensure_ascii=False)
    return json.dumps({
        "summary": f"[mock] {instruction.strip()[:40]}",
        "ops": [{"eid": m.group(1), "op": "style",
                 "style": {"text-shadow": "0 1px 2px rgba(0,0,0,.3)"}}],
    }, ensure_ascii=False)
