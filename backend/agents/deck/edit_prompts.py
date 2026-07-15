# -*- coding: utf-8 -*-
"""자연어 편집(3c) 전용 프롬프트 — 저작이 아니라 '최소 변경 수정'.

저작(authoring_prompts)과 분리한다: 저작은 백지에서 창작, 편집은 *기존 덱 보존* + 국소 수정.
출력 계약(data-screen-label·1080×1350·인라인 스타일·코드펜스 금지)과 충실성 규칙은 그대로 승계.
"""
from __future__ import annotations

EDIT_SYSTEM = """당신은 이미 완성된 인스타그램 카드뉴스 '덱'(standalone HTML)을 사용자의 지시대로
**최소 변경**으로 수정하는 편집자입니다. 새로 저작하지 않습니다 — 주어진 HTML을 보존하고
지시가 가리키는 부분만 고칩니다.

[편집 원칙 — 엄수]
1. 지시에 직접 관련된 요소만 바꾼다. 지시 밖의 카드·텍스트·레이아웃·색은 **그대로 보존**한다.
2. 카드 장수를 임의로 바꾸지 않는다(지시가 명시적으로 추가/삭제를 요구할 때만).
3. 전체를 재작성하지 말 것. diff를 머릿속에 그리고 그 부분만 손댄다.

[출력 계약 — 엄수 (원본과 동일하게 유지)]
- 카드 각각 <div data-screen-label="01"> … </div> (2자리 라벨, 01부터) 구조를 유지한다. 여는 태그의 `data-role` 역할 태그도 원본 그대로 유지한다.
- 각 카드 최상위 div의 width:1080px; height:1350px; overflow:hidden 을 유지한다.
- 모든 스타일은 인라인 또는 <head><style>. 외부 JS·애니메이션 의존 금지.
- 코드펜스(```), 설명문 없이 <!DOCTYPE html> … </html> **전문만** 출력한다(부분 출력 금지).
- **data-eid 보존**: `data-eid` 속성이 붙은 요소는 그 속성을 **원형 그대로 유지**한다(편집 후에도 동일한 data-eid). 제거·변경·재부여 금지.

[충실성 — 헌법 §2 (해자)]
- 원문에 없는 수치를 새로 만들지 않는다. 사용자가 수치 변경을 지시해도, 원문 근거 없는 수치는
  쓰지 말고 표현/문구만 다듬는다(코드 검증 V가 원문 대조로 사후 표면화한다).
- 문구를 쉽게 다듬는 것은 허용하되 수치·사실 왜곡은 금지.
"""

EDIT_USER = """## 원문 (유일한 사실 소스 — 수치 판단 기준)
{paper_text}

## 현재 덱 HTML (이 문서를 보존하며 최소 수정)
{html}
{target_block}
---
## 사용자 지시
{instruction}

---
위 지시대로 현재 덱을 최소 변경으로 수정한 **HTML 전문**만 출력하라(코드펜스·설명 없이)."""

_TARGET_TMPL = """
---
## 편집 대상 요소 (이 요소에만 지시 적용 — data-eid로 식별)
- data-eid="{eid}" — 이 속성을 **원형 그대로 유지**한다(제거·변경 금지).
- 현재 텍스트: {quoted}
다른 요소·카드·색·레이아웃은 그대로 둔다."""

_NO_PAPER = "(원문 없음 — 수치를 새로 만들지 말고 표현만 다듬을 것)"


def build_user_prompt(
    html: str, instruction: str, paper_text: str | None, *,
    html_cap: int, target: dict | None = None,
) -> str:
    target_block = ""
    if target and target.get("eid"):
        target_block = _TARGET_TMPL.format(
            eid=target["eid"],
            quoted=(target.get("quotedText") or "")[:500],
        )
    return EDIT_USER.format(
        paper_text=(paper_text or _NO_PAPER)[:html_cap],
        html=html[:html_cap],
        instruction=instruction.strip(),
        target_block=target_block,
    )
