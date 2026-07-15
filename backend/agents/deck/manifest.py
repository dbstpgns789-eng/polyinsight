# -*- coding: utf-8 -*-
"""PI_MANIFEST / PI_SELFCHECK — 저작 콜의 편집 결정·자가판정 파싱 + 반복이력 주입.

선언은 같은 콜 안의 chain-of-thought(한 마음, 헌법 §1)다 — architect/writer 분리가 아니다.
코드는 형태를 강제하지 않는다: 파싱 실패는 **경고 사유일 뿐 파이프라인 실패가 아니다**(소프트).

★반복이력이 다양성 엔진인 이유: 모델은 자기가 지난주에 뭘 만들었는지 모른다.
  덱 간 동질화를 깨는 정보(이력)는 파이프라인만 갖고 있다. temperature를 올리는 건 답이 아니다
  — 취향 없는 노이즈만 늘어난다.
"""
from __future__ import annotations

import json
import re

_MANIFEST_RE = re.compile(r"<!--\s*PI_MANIFEST\s*(\{.*?\})\s*-->", re.S)
_SELFCHECK_RE = re.compile(r"<!--\s*PI_SELFCHECK\s*(\{.*?\})\s*-->", re.S)

# 자기신고 키의 극성: 결함을 묻는 키(true=결함) vs 정상을 묻는 키(false=결함)
_DEFECT_IF_TRUE = {"placeholder", "emoji"}


def parse_manifest(html: str) -> dict | None:
    """덱 HTML에서 PI_MANIFEST JSON 추출(아크·킬러자산·팔레트·모티프·버린아크). 없거나 깨졌으면 None."""
    m = _MANIFEST_RE.search(html)
    if not m:
        return None
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def selfcheck_failures(html: str) -> list[str]:
    """PI_SELFCHECK에서 모델이 스스로 '실패'라 신고한 항목 이름들. 없으면 빈 리스트.

    자기신고라 신뢰의 정본은 아니다 — V(코드)·저지(비전)와의 삼각측량 신호로만 쓴다(경고 표면화).
    """
    m = _SELFCHECK_RE.search(html)
    if not m:
        return []
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(obj, dict):
        return []
    fails: list[str] = []
    for k, v in obj.items():
        if not isinstance(v, bool):
            continue
        if (k in _DEFECT_IF_TRUE and v) or (k not in _DEFECT_IF_TRUE and not v):
            fails.append(k)
    return fails


def build_history_block(recent: list[dict]) -> str:
    """최근 덱 매니페스트 → 소프트 변주 선호 텍스트. 이력 없으면 빈 문자열.

    **하드 금지가 아니다** — 최근 3편이 진짜로 데이터 클라이맥스가 맞는데 4편째를 억지로 딴 아크로
    밀면 적합도를 희생한다. 적합이 신선함을 이긴다.
    """
    if not recent:
        return ""
    lines = ["## 이 계정의 최근 발행 덱 (변주 참고)"]
    for m in recent:
        lines.append(f"- 아크: {m.get('archetype', '?')} / 팔레트: {m.get('palette', '?')}"
                     f" / 모티프: {m.get('motif', '?')}")
    lines.append("정확 반복은 피하되, 이 논문이 허락하는 선에서 변주하라. 적합이 신선함을 이긴다.")
    return "\n".join(lines) + "\n\n"
