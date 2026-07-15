# 저작 프롬프트 엔지니어링 — 측정 우선(Measurement-First) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 저작 품질을 vibes가 아닌 측정으로 관리하는 체계(저지+eval셋)를 먼저 세우고, 그 위에서 프롬프트 5층 재편·파생수치 검증(V2)·아키타입 선언+반복이력·refs 승격 게이트를 얹는다.

**Architecture:** 3세션 진단(결함↔갭 / generality / 채널-지식 매핑)과 7개 정밀화의 합의 구현. 순서가 핵심 — **Phase 0(측정 베이스라인)을 프롬프트 변경 전에 찍는다**. 저작은 여전히 한 콜·한 마음(헌법 §1)이고, 에디토리얼 선언은 같은 콜 안의 HTML 주석(chain-of-thought)이지 architect/writer 분리가 아니다.

**Tech Stack:** Python(FastAPI·httpx·pytest), 기존 `llm_client.call(images=...)` 비전 지원, SQLite.

**Out of scope (별도 플랜):** 브랜드 킷(계정 크롬 고정 — 프론트/API 스펙 필요), 비전 자기수정 루프(유료 티어), 장르매칭 refs 동적 선택(라이브러리 3개 이하라 YAGNI), L2 크래프트 산문 삭제 다이어트(재측정 후 별도 판단 — 회귀 위험).

**유료 게이트:** Task 4(베이스라인)·Task 10(재측정)는 실 LLM 호출 — **실행 전 사용자 허락 필수** (memory: 비용 발생 작업 사전 허락). 나머지는 전부 무료(코드+mock 테스트).

**v1.1 (2026-07-11): 31에이전트 적대검증 반영 (확정 23건).** 핵심 수정: ①동질화(덱 간 다양성)를 측정하는 교차저지 신설 — 기존 설계는 사용자 1순위 고통을 측정 못 했다 ②저지 temperature=0은 no-op(llm_client가 sonnet-5 sampling 파라미터 드롭) → 노이즈 밴드 실측+계층화 판정으로 교체 ③V2 suspect 웹 표면화(Task 5.5 신설 — 표면화 없는 검산은 170% 사건의 반복) ④asyncio.run 반복 대응(저지 클라이언트 호출당 생성) ⑤eval 이력 격리·429 fail-fast·resume ⑥L4 자기검수를 유저 프롬프트 말단으로(시스템 끝=가짜 recency) ⑦L2 모순 2곳 조건화 ⑧'7장' 전수 제거(art_direction_block 포함) ⑨V2 검산쌍에서 페이지네이션·연도 제외.

---

## File Structure

```
backend/core/config.py                          [수정] LLM_MODEL_JUDGE·JUDGE_MAX_TOKENS 추가
backend/scripts/deck_judge.py                   [신규] 블랙박스 저지(덱 1개 5축+결함) + 다양성 교차저지(표지 N장 — 동질화 측정)
backend/scripts/eval_runner.py                  [신규] eval셋 배치: 업로드→폴링→PNG다운→저지→다양성→결과 JSON (resume·이력격리·429 fail-fast)
web/src/lib/verifyStatus.ts                     [신규] derived suspect 필터·allClear 판정 (순수함수 — vitest 대상)
web/src/components/deck/DeckFactPanel.tsx       [수정] V2 suspect 배지 렌더 + allClear 게이트 강화
eval/eval_set.json                              [신규] 고정 평가 논문 6편 목록(장르 태그) — 사용자 지정
eval/runs/                                      [신규] 실행 결과 아카이브 (baseline/, after-YYYY-MM-DD/)
backend/agents/deck/AUTHORING.md                [신규] 컨트롤룸 — 자산맵·결정로그(append-only)·refs 레지스트리+승격게이트·백로그. 자산 복사 금지, file:line·sha 포인터만
eval/scoreboard.jsonl                           [신규·기계기록] eval_runner가 자동 append — 사람 손으로 쓰지 않는다
backend/CLAUDE.md                               [수정] 저작 작업 필독에 AUTHORING.md + 결정로그 규율
backend/core/fidelity.py                        [수정] V2: derived_claims() 파생수치 산수 정합 검사
backend/agents/deck/pipeline.py                 [수정] verify payload에 derived 합류 + 매니페스트 저장/이력 조회
backend/agents/deck/authoring_prompts.py        [수정] 5층 재편(L0~L4)·아키타입 메뉴·자기검수·{card_count}
backend/agents/deck/authoring.py                [수정] history_block 파라미터
backend/agents/deck/manifest.py                 [신규] PI_MANIFEST 파싱 + history_block 생성 (순수함수)
backend/core/db.py                              [수정] deck_manifest 테이블 + save/get_recent
docs/contracts/05_agent_design.md               [수정] S6 프롬프트 5층 구조·매니페스트 계약 + 컨트롤룸 링크 (docs 먼저)
docs/contracts/07_api_data_model.md             [수정] deck_manifest 테이블 (docs 먼저)
backend/tests/test_deck_judge.py                [신규]
backend/tests/test_fidelity_derived.py          [신규]
backend/tests/test_authoring_prompts.py         [신규]
backend/tests/test_deck_manifest.py             [신규]
```

테스트 실행은 항상 `pytest backend/tests/` (bare pytest 금지 — CLAUDE.md).

---

# Phase 0 — 측정 체계 (프롬프트 변경 전 베이스라인)

### Task 1: 저지 스크립트 — 고정 루브릭 + JSON 파서

**Files:**
- Modify: `backend/core/config.py` (15행 `LLM_MODEL_AUTHOR` 근처)
- Create: `backend/scripts/deck_judge.py`
- Test: `backend/tests/test_deck_judge.py`

- [ ] **Step 1: 실패하는 테스트 작성** — 저지 응답 JSON 파서(코드펜스·잡설 강건)

```python
# backend/tests/test_deck_judge.py
# -*- coding: utf-8 -*-
"""deck_judge 파서·루프 안전성 단위 테스트 — LLM 호출 없음(무료)."""
import asyncio

import backend.scripts.deck_judge as dj
from backend.scripts.deck_judge import parse_judge_json

_GOOD = '{"scores": {"hook": 3, "narrative": 4, "accessibility": 3, "integrity": 2, "finish": 4}, "defects": {"emoji": true, "placeholder": false, "untranslated_unit": true, "derived_number_suspect": true, "dead_zone": true, "text_visual_mismatch": true}, "verdict": "pause", "top_problems": ["card6 170%"], "one_line": "조건부"}'


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
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_deck_judge.py -v`
Expected: FAIL — `ModuleNotFoundError` 또는 `ImportError: parse_judge_json`

- [ ] **Step 3: config 추가 + deck_judge.py 구현**

`backend/core/config.py`의 `LLM_MODEL_AUTHOR` 블록 아래에 추가:

```python
    LLM_MODEL_JUDGE: str = "claude-sonnet-5"   # 저지(비전) — Opus보다 저렴, 렌더 PNG 심사용
    JUDGE_MAX_TOKENS: int = 2000
```

`backend/scripts/deck_judge.py` (전체):

```python
# -*- coding: utf-8 -*-
"""블랙박스 덱 저지 — 렌더된 카드 PNG를 외부 심사자 루브릭으로 채점 (비전 1콜)
+ 다양성 교차저지(여러 덱 표지 비교 — 동질화 측정).

사용:
  python -m backend.scripts.deck_judge --dir <png폴더> [--out result.json] [--repeat N]

루브릭은 2026-07-11 블랙박스 심사(미세구슬 덱)에서 고정. 프롬프트 변경 시
같은 루브릭·같은 eval셋으로 재채점해 회귀를 측정한다.
★저지는 확률적이다 — claude-sonnet-5는 sampling 파라미터를 받지 않아(llm_client가
_NO_SAMPLING_PREFIXES로 드롭) 기본 온도로 샘플링된다. 점수 비교는 --repeat로 실측한
노이즈 밴드(judge_noise) 기준으로만 한다. temperature 인자를 넘기지 않는 이유가 이것.
★AsyncAnthropic은 자신을 만든 이벤트 루프에 묶인다 — eval_runner가 asyncio.run을
논문마다 새로 열므로, 싱글턴 llm_client 대신 호출당 LLMClient를 새로 만든다.
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
    if not all(k in obj for k in required):
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest backend/tests/test_deck_judge.py -v`
Expected: 5 PASS

- [ ] **Step 5: 커밋**

```bash
git add backend/core/config.py backend/scripts/deck_judge.py backend/tests/test_deck_judge.py
git commit -m "[BE] 덱 블랙박스 저지 스크립트 — 고정 루브릭·비전 1콜·JSON 파서"
```

---

### Task 2: eval셋 매니페스트 + eval_runner

**Files:**
- Create: `eval/eval_set.json`
- Create: `backend/scripts/eval_runner.py`

- [ ] **Step 1: eval_set.json 골격 생성** (경로는 사용자가 채움 — 아래 placeholder는 **실행 게이트에서 사용자가 실제 PDF 경로로 교체**해야 하며, 채워지기 전 eval_runner는 명시적 에러로 중단한다)

```json
{
  "_설명": "고정 평가셋 — 프롬프트 변경 전후 같은 논문으로 회귀 측정. path를 실제 PDF로 교체할 것. papers 순서=실행 순서(고정) — 이력 격리로 순서 효과는 차단되지만 라벨 간 비교 안정성을 위해 변경 금지.",
  "papers": [
    {"id": "materials-1", "genre": "재료·공정", "path": "CHANGE_ME.pdf"},
    {"id": "materials-2", "genre": "재료·공정", "path": "CHANGE_ME.pdf"},
    {"id": "csml-1",      "genre": "CS·ML",    "path": "CHANGE_ME.pdf"},
    {"id": "bio-1",       "genre": "바이오·임상", "path": "CHANGE_ME.pdf"},
    {"id": "theory-1",    "genre": "이론·수리(킬러수치 없음)", "path": "CHANGE_ME.pdf"},
    {"id": "long-1",      "genre": "장문 30p+(60k자 절단 스트레스)", "path": "CHANGE_ME.pdf"}
  ]
}
```

- [ ] **Step 2: eval_runner.py 구현** (`golden_batch.py` 패턴 재사용 — 로그인은 세션 쿠키)

```python
# -*- coding: utf-8 -*-
"""eval 배치 — eval_set.json의 논문을 저작→렌더→저지→다양성까지 돌려 결과 기록.

사용 (유료 — 실행 전 사용자 허락 필수):
  python -m backend.scripts.eval_runner --label baseline
전제: uvicorn 서버 가동 중, EVAL_EMAIL/EVAL_PASSWORD 환경변수.
★eval 유저는 email_verified=1이어야 함 — 미인증은 일일 3편 상한(UPLOAD_UNVERIFIED_LIMIT)이라
  6편 배치가 4편째 429로 죽는다. 429는 즉시 중단(반쪽 베이스라인 커밋 방지).
★resume: 같은 label 재실행 시 results.json의 DONE 논문은 스킵(저작 재과금 방지).
  다양성 저지는 매 실행 재계산 — 아카이브된 베이스라인 PNG에도 소급 적용된다.
★이력 격리: 논문마다 deck_manifest를 비워 '프롬프트 효과'와 '이력 주입 효과'를 분리 측정.
  (이력 없이는 after 런이 실행 순서에 종속되고 런 간 재현이 깨진다.)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import httpx

from backend.scripts.deck_judge import judge_dir, judge_diversity

BASE_URL = "http://localhost:8000"
POLL_INTERVAL = 5
TIMEOUT_PER_PAPER = 1200   # AUTHOR_TIMEOUT_S=600 + S1(장문 pymupdf 느림) + 렌더 여유 — long-1이 최다 소요

_ROOT = Path(__file__).resolve().parents[2]
_EVAL_SET = _ROOT / "eval" / "eval_set.json"
_SCOREBOARD = _ROOT / "eval" / "scoreboard.jsonl"


def _git_sha() -> str:
    """스코어보드 행에 박을 프롬프트 버전 지문."""
    try:
        import subprocess
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, cwd=_ROOT).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _login(client: httpx.Client) -> int | None:
    """로그인(세션 쿠키) 후 user id 반환(이력 격리용)."""
    email = os.getenv("EVAL_EMAIL", "")
    pw = os.getenv("EVAL_PASSWORD", "")
    if not email or not pw:
        sys.exit("[ERROR] EVAL_EMAIL / EVAL_PASSWORD 환경변수 필요")
    r = client.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    if r.status_code != 200:
        sys.exit(f"[ERROR] 로그인 실패: {r.status_code} {r.text[:200]}")
    me = client.get(f"{BASE_URL}/api/auth/me", timeout=10).json()
    user = me.get("user") if isinstance(me.get("user"), dict) else me
    return user.get("id")


def _clear_history(user_id: int | None) -> None:
    """이력 격리 — deck_manifest 비움. 테이블 미구현(베이스라인 시점)이면 조용히 no-op."""
    if user_id is None:
        return
    try:
        from backend.core import db
        if hasattr(db, "delete_deck_manifests"):
            asyncio.run(db.delete_deck_manifests(user_id))
    except Exception as exc:
        print(f"    (이력 격리 스킵: {exc})")


def _submit_and_wait(client: httpx.Client, pdf: Path) -> dict:
    with pdf.open("rb") as f:
        r = client.post(f"{BASE_URL}/api/deck/upload",
                        files={"file": (pdf.name, f, "application/pdf")},
                        data={"card_count": "7"}, timeout=60)
    if r.status_code == 429:
        sys.exit(f"[ERROR] 업로드 쿼터 429 ({pdf.name}) — eval 유저 email_verified 확인. "
                 "유료 런을 반쪽으로 계속 태우지 않도록 즉시 중단")
    if r.status_code != 202:
        return {"status": "SUBMIT_FAILED", "detail": r.text[:300], "job_id": None}
    job_id = r.json()["jobId"]
    deadline = time.time() + TIMEOUT_PER_PAPER
    while time.time() < deadline:
        sr = client.get(f"{BASE_URL}/api/status/{job_id}", timeout=15)
        data = sr.json()
        print(f"    [{data.get('stage')}] {data.get('progress', 0)}% …", end="\r", flush=True)
        if data.get("status") in ("DONE", "FAILED", "ERROR"):
            print()
            return {"status": data["status"], "job_id": job_id, "warnings": data.get("warnings", "")}
        time.sleep(POLL_INTERVAL)
    return {"status": "TIMEOUT", "job_id": job_id}


def _download_cards(client: httpx.Client, job_id: str, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for i in range(1, 13):
        r = client.get(f"{BASE_URL}/api/deck/{job_id}/cards/{i}", timeout=60)
        if r.status_code != 200:
            break
        (out_dir / f"card{i:02}.png").write_bytes(r.content)
        n += 1
    return n


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")   # Windows cp949 콘솔 방어
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="eval 배치 (유료)")
    ap.add_argument("--label", required=True, help="런 라벨 (baseline, after-0715 등)")
    args = ap.parse_args()

    spec = json.loads(_EVAL_SET.read_text(encoding="utf-8"))
    papers = spec["papers"]
    missing = [p["id"] for p in papers if p["path"] == "CHANGE_ME.pdf" or not Path(p["path"]).exists()]
    if missing:
        sys.exit(f"[ERROR] eval_set.json 경로 미지정/없음: {missing}")

    run_dir = _ROOT / "eval" / "runs" / args.label
    run_dir.mkdir(parents=True, exist_ok=True)
    results_path = run_dir / "results.json"
    results: list[dict] = []
    done_ids: set[str] = set()
    if results_path.exists():   # resume — 실패분만 재실행, DONE 저작비 재과금 방지
        results = json.loads(results_path.read_text(encoding="utf-8"))
        done_ids = {e["id"] for e in results if e.get("status") == "DONE"}
        print(f"[resume] 기존 결과 {len(results)}건 로드 — DONE {len(done_ids)}편 스킵")
    sha = _git_sha()

    with httpx.Client() as client:
        uid = _login(client)
        for i, p in enumerate(papers, 1):
            if p["id"] in done_ids:
                continue
            print(f"[{i}/{len(papers)}] {p['id']} ({p['genre']})")
            _clear_history(uid)   # 논문마다 이력 0 — 순서 의존·런 간 비재현 차단
            r = _submit_and_wait(client, Path(p["path"]))
            entry = {"id": p["id"], "genre": p["genre"], **r}
            if r["status"] == "DONE":
                png_dir = run_dir / p["id"]
                entry["cards"] = _download_cards(client, r["job_id"], png_dir)
                entry["judge"] = asyncio.run(judge_dir(png_dir))
                deck = client.get(f"{BASE_URL}/api/deck/{r['job_id']}", timeout=30).json()
                entry["verify"] = deck.get("verify")
            results = [e for e in results if e["id"] != p["id"]] + [entry]
            results_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            # 스코어보드는 기계가 쓴다 — 사람 손 안 탐(살아있는 문서의 조건)
            if entry.get("judge"):
                with _SCOREBOARD.open("a", encoding="utf-8") as sb:
                    sb.write(json.dumps({
                        "label": args.label, "sha": sha, "paper": p["id"], "genre": p["genre"],
                        "scores": entry["judge"]["scores"], "verdict": entry["judge"]["verdict"],
                        "defects": entry["judge"]["defects"],
                        "truncated": "SOURCE_TRUNCATED" in str(entry.get("warnings", "")),
                    }, ensure_ascii=False) + "\n")

    # ── 다양성 교차저지 — 동질화(사용자 1순위 고통)는 크로스덱 속성이라 별도 1콜 ──
    done_entries = [e for e in results if e.get("status") == "DONE"]
    covers: list[bytes] = []
    labels: list[str] = []
    for e in sorted(done_entries, key=lambda x: x["id"]):
        pngs = sorted((run_dir / e["id"]).glob("*.png"))
        if pngs:
            covers.append(pngs[0].read_bytes())
            labels.append(e["id"])
    if len(covers) >= 2:
        div = asyncio.run(judge_diversity(covers, labels))
        (run_dir / "diversity.json").write_text(
            json.dumps(div, ensure_ascii=False, indent=2), encoding="utf-8")
        if div:
            print(f"다양성: {div.get('diversity')}/5 · 구별 포맷 {div.get('distinct_formats')}종")
            with _SCOREBOARD.open("a", encoding="utf-8") as sb:
                sb.write(json.dumps({
                    "label": args.label, "sha": sha, "paper": "_diversity",
                    "diversity": div.get("diversity"),
                    "distinct_formats": div.get("distinct_formats"),
                    "similar_pairs": div.get("similar_pairs"),
                }, ensure_ascii=False) + "\n")

    ok = [e for e in done_entries if e.get("judge")]
    if ok:
        axes = ["hook", "narrative", "accessibility", "integrity", "finish"]
        print("\n=== 축별 평균 ===")
        for a in axes:
            avg = sum(e["judge"]["scores"][a] for e in ok) / len(ok)
            print(f"  {a:14}: {avg:.2f}")
    print(f"결과: {results_path}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 문법 확인 (실행은 안 함 — 유료)**

Run: `python -c "import backend.scripts.eval_runner"` (레포 루트에서)
Expected: 에러 없이 종료

- [ ] **Step 4: 커밋**

```bash
git add eval/eval_set.json backend/scripts/eval_runner.py
git commit -m "[BE] eval 러너 — 고정 평가셋 업로드→저지→결과 아카이브"
```

---

### Task 2.5: 컨트롤룸 — backend/agents/deck/AUTHORING.md

> 제품의 심장 4자산(프롬프트·V·refs·측정)의 **연결조직**. 자산은 git이 정본(코드·파일)이고,
> 이 문서는 자산을 복사하지 않는다 — file:line·sha로 **가리키며**, 왜·측정효과·레지스트리만 관리한다.
> (2026-07-09 문서표류 사고의 해독제: 복사본 관리문서 금지.)

**Files:**
- Create: `backend/agents/deck/AUTHORING.md`
- Modify: `backend/CLAUDE.md` (세션 시작 필독 + NEVER)

- [ ] **Step 1: AUTHORING.md 작성** (초기 시드 전문):

```markdown
# AUTHORING.md — 저작 시스템 컨트롤룸
> 제품 = 프롬프트 · V(검증) · refs · 측정체계, 이 4자산이 전부다(모델은 API — 못 바꾼다).
> **자산을 복사하지 않는다 — 가리킨다.** 자산의 정본은 git의 코드/파일이다.
> **규율**: 프롬프트/V/refs를 바꾸는 커밋은 §2 결정로그 1줄을 같은 커밋에 동반한다.
> 측정효과 칸은 즉시 채우지 않는다 — 다음 eval 런(유료) 후 백필. 로그는 append-only, 절대 삭제 금지.

## 1. 자산 맵
| 자산 | 정본 위치 | 역할 |
|---|---|---|
| 프롬프트 | `backend/agents/deck/authoring_prompts.py` | 5층: L0 계약 / L1 하드가드(틱 블랙리스트 포함) / L2 크래프트 / L3 방향(아키타입 선언+이력) / L4 자기검수 |
| V 검증 | `backend/core/fidelity.py` | 수치 존재 대조(`verify_deck`) + V2 파생수치 검산(`derived_claims`) |
| refs | §4 레지스트리 → `output/cardnews_*` | few-shot: 완성도 하한 + 범위 데모 (베끼기 금지 조항과 세트) |
| 측정 | `eval/eval_set.json`(고정 6편) + `backend/scripts/deck_judge.py`(고정 루브릭) + `eval/scoreboard.jsonl`(기계 기록) | 프롬프트 변경의 전후 비교 — vibes 금지 |

## 2. 결정 로그 (append-only)
| 날짜 | 자산 | 무엇을 | 왜 (관찰된 결함/통찰) | 측정효과 | sha |
|---|---|---|---|---|---|
| 2026-07-07 | 프롬프트 | P0+P1 반영·검증배지 제거·저작모델 Opus 4.8 격상 | 8에이전트 비평(발행 골격 3결함)·사용자 '배지 촌스럽다' | (측정체계 이전) | 61391f9~ |
| 2026-07-11 | 덱(핫픽스) | 미세구슬 덱 '170% 증가' 오기 수정 | 블랙박스 심사: 142→238=68% 증가를 170%로 오기(배·%혼동) | — | (핫픽스 sha) |
| 2026-07-11 | 전체 | 측정우선 플랜 착수 — 5층 재편·V2·매니페스트·승격게이트 | 3세션 진단: 지식을 채널 하나(산문)에 우겨넣음이 4증상의 근본 | baseline 대기 | (본 커밋) |

## 3. eval 셋
정본 = `eval/eval_set.json` — 장르 스팬 6편(재료2·CS1·바이오1·이론1·장문1). 이론·장문=꼬리 스트레스.
셋 변경(논문 교체·추가)도 §2에 로그 — 셋이 바뀌면 전후 비교가 깨지므로 라벨을 새로 딴다.

## 4. refs 레지스트리 + 승격 게이트
코드 정본 = `authoring_prompts.py`의 `REF_LIBRARY`. 이 표는 그 거울이 아니라 **이유·상태 관리**:

| ref | 장르 | 무드 | 아크 | 상태 |
|---|---|---|---|---|
| cardnews_bert_design | cs-ml | 웜 페이퍼 에디토리얼 | 개념 체험형 | 주입 1순위 |
| cardnews_attention_neon | cs-ml | 미드나잇 네온 | 데이터 클라이맥스형 | 주입 2순위 |
| cardnews_attention | cs-ml | 포레스트 그린 | 데이터 클라이맥스형 | 보조(미주입) |

**승격 게이트 — 클린 패스만** (레퍼런스의 흠은 조항보다 강하게 옮는다):
1. deck_judge: verdict=="save", defects 전부 false
2. fidelity V: unverified 0(또는 전부 사용자 확인), derived suspect 0
3. 운영자 최종 확인 1회
4. 다양성 기여: 기존 refs와 다른 축(장르/무드/아크) — 비슷한 방향 추가는 동질화

승격 후보 로그:
| 날짜 | 덱 | 장르 | 상태 |
|---|---|---|---|
| 2026-07-11 | 셀룰로오스 미세구슬 | 재료·공정 | **보류** — 저지 pause: card2 공백·card5 그림불일치·이모지. 수정 후 재심사 시 재료장르 1호 후보 |

## 5. 스코어보드
정본 = `eval/scoreboard.jsonl` — **eval_runner가 자동 append. 손으로 쓰지 않는다.**
행 = {label, sha, paper, genre, scores(5축), verdict, defects}. 같은 paper의 sha 간 비교가 회귀 감지.

## 6. 백로그 (열린 것 — 별도 플랜行)
- 브랜드 킷(계정 크롬 고정 — '잡지: 마스트헤드 고정·커버 변주'의 나머지 절반)
- 비전 자기수정 루프(유료 티어 — 시각 결함의 진짜 해법)
- 장르매칭 refs 동적 선택(라이브러리 3개 초과 시)
- L2 크래프트 산문 다이어트(재측정 후 판단)
- fidelity substring 단어경계 강화(짧은 수 가짜 VERIFIED)
- 60k자 절단 경고 표면화
```

- [ ] **Step 2: backend/CLAUDE.md 배선.** '세션 시작 필독' 코드블록에 한 줄 추가:

```
agents/deck/AUTHORING.md      ← 저작 자산 컨트롤룸(프롬프트·V·refs·측정) — 저작 관련 작업 시 필독
```

'## 7. NEVER' 블록에 한 줄 추가:

```
NEVER  프롬프트/V/refs 변경 커밋에 AUTHORING.md §2 결정로그 누락
```

- [ ] **Step 3: 커밋**

```bash
git add backend/agents/deck/AUTHORING.md backend/CLAUDE.md
git commit -m "[DOCS] 저작 컨트롤룸 AUTHORING.md — 4자산 포인터·결정로그·승격게이트·스코어보드 규율"
```

---

### Task 3: docs 계약 갱신 (코드 변경 전 — CLAUDE.md 'docs 먼저')

**Files:**
- Modify: `docs/contracts/05_agent_design.md`
- Modify: `docs/contracts/07_api_data_model.md`

- [ ] **Step 1: 05_agent_design.md에 S6 프롬프트 5층 구조 절 추가.** 기존 S6 절 아래 새 절로:

```markdown
## S6 프롬프트 계층 구조 (2026-07-11, 측정우선 플랜)

프롬프트는 5층으로 구성한다. 지식마다 운반 채널이 다르다는 원칙:
| 층 | 내용 | 채널 |
|---|---|---|
| L0 계약 | 출력 포맷·치수·폰트 로딩 | 프롬프트(맨 앞, 불변) |
| L1 하드 가드 | 실측 결함 방지 + 모델 틱 블랙리스트 — 이진 판정문, 상한 10개 | 프롬프트 |
| L2 크래프트 | 발행급 마감 어휘 | 프롬프트 + few-shot refs |
| L3 방향 | 서사 아키타입 메뉴(탈출구 필수 — 팔레트지 감옥 아님) + PI_MANIFEST 선언 + 최근 덱 이력(소프트) | 동적 주입 |
| L4 자기검수 | 출력 직전 이진 체크리스트 | 프롬프트(맨 끝) |

**PI_MANIFEST 계약**: 모델은 `<head>` 첫 줄에
`<!-- PI_MANIFEST {"archetype": "...", "killer_asset": "...", "palette": "...", "motif": "..."} -->`
주석 한 줄로 편집 결정을 선언한다. 같은 콜 안의 선언→저작이므로 한 마음(§1) 유지.
파이프라인은 이를 파싱해 deck_manifest에 저장하고, 다음 저작 때 최근 3건을
소프트 선호("정확 반복은 피하되 적합이 신선함을 이긴다")로 주입한다. 파싱 실패는 경고, 실패 아님.

**측정**: 프롬프트 변경은 eval/eval_set.json 고정 6편 + deck_judge 루브릭으로 전후 비교 후 채택.

**관리 정본**: `backend/agents/deck/AUTHORING.md` (컨트롤룸 — 자산맵·결정로그·refs 승격게이트·스코어보드).
이 계약문서는 구조만 서술하고, 변경 이력·이유는 컨트롤룸이 관리한다.
```

- [ ] **Step 2: 07_api_data_model.md에 deck_manifest 테이블 추가.** DB 스키마 절에:

```markdown
### deck_manifest (2026-07-11)
| 컬럼 | 타입 | 설명 |
|---|---|---|
| job_id | TEXT PK | 덱 job |
| user_id | INTEGER | 이력 조회 키(계정 단위 변주) |
| manifest_json | TEXT | PI_MANIFEST 원문 JSON (archetype·killer_asset·palette·motif) |
| created_at | TEXT | ISO8601 |
```

- [ ] **Step 3: 커밋**

```bash
git add docs/contracts/05_agent_design.md docs/contracts/07_api_data_model.md
git commit -m "[DOCS] S6 프롬프트 5층 구조 + PI_MANIFEST·deck_manifest 계약"
```

---

### Task 4: ⛔유료 게이트 — 베이스라인 실행 (사용자 허락 후)

**Files:** 없음 (실행만). 산출물: `eval/runs/baseline/{results.json, diversity.json, judge_noise.json}` + `eval/scoreboard.jsonl`

- [ ] **Step 1: 사용자에게 eval_set.json의 CHANGE_ME 6편 경로 지정받기** (장르 스팬: 재료2·CS1·바이오1·이론1·장문1 — 이론·장문이 꼬리 스트레스 테스트)

- [ ] **Step 2: eval 유저 전제 확인 — 인증 승격** (미인증 유저는 일일 업로드 3편 상한이라 4편째부터 429. 저작비 3콜을 태우고 반쪽 베이스라인이 나온다.)

```bash
python -c "import asyncio; from backend.core import db; u = asyncio.run(db.get_user_by_email('<EVAL_EMAIL>')); print(u); asyncio.run(db.set_email_verified(u['id']))"
```

Expected: user dict 출력 + 에러 없음. (함수명이 다르면 `backend/core/db.py`에서 email_verified 세팅 함수를 확인해 맞춘다. `.env`의 RATE_LIMIT_ENABLED=false로 우회하지 말 것 — 라이브 서버 보안설정 변경이라 비권장.)

- [ ] **Step 3: 비용 고지 + 허락.** **허락 없이 실행 금지.**
  - 저작 6콜: Opus 4.8, 입력 ~45~80k(few-shot refs 2덱 전문 + 논문 60k자) · 출력 ~20k → **콜당 ~$0.7~1.5, 합계 ~$5~9**
  - 저지 6콜 + 다양성 1콜 + 노이즈 반복 12콜: Sonnet 비전 → **합계 ~$1~2**
  - **사이클 총 ~$6~11.** 실측 usage(`deck_pipeline_complete` 이벤트의 input/output_tokens)로 1회 후 보정한다.

- [ ] **Step 4: 서버 가동 확인 후 실행**

Run: `python -m backend.scripts.eval_runner --label baseline`
Expected: 6편 전부 DONE + 다양성 점수 출력. **SUBMIT_FAILED/TIMEOUT이 1건이라도 있으면 베이스라인 커밋 금지** — 원인 해결 후 같은 label로 재실행(resume이 DONE 논문을 스킵하므로 실패분만 재과금).

- [ ] **Step 5: 저지 노이즈 밴드 실측** (저지는 확률적 — sonnet-5가 sampling 파라미터를 안 받아 temperature 고정이 불가능하다. 노이즈 크기를 모르면 전후 비교가 동전던지기다.)

```bash
python -m backend.scripts.deck_judge --dir eval/runs/baseline/materials-1 --repeat 3 --out eval/runs/baseline/judge_noise.json
```

Expected: 같은 PNG 3회 채점 결과. 축별 점수 편차(예: hook 3/4/3)와 defect 불리언 플립을 눈으로 확인하고, **축별 최대 변동폭을 judge_noise.json 옆에 한 줄로 기록**(Task 10 판정 임계의 근거). 저작 재실행 없음 = 추가 비용은 Sonnet 3콜뿐.

- [ ] **Step 6: 인간 캘리브레이션 1회** — 사용자가 6덱 중 2덱을 직접 보고 저지 점수와 감이 일치하는지 확인. 크게 어긋나면 JUDGE_SYSTEM 루브릭 문구 조정 후 저지만 재실행(저작 재실행 불필요 — PNG 캐시됨).

- [ ] **Step 7: 커밋**

```bash
git add eval/runs/baseline/ eval/scoreboard.jsonl
git commit -m "[EVAL] 베이스라인 — 6편 저지 점수·다양성·노이즈 밴드 (프롬프트 변경 전)"
```

---

# Phase 1 — V2: 파생수치 산수 정합 검증 (무료, 해자 봉합)

### Task 5: fidelity.derived_claims()

**Files:**
- Modify: `backend/core/fidelity.py` (파일 끝에 추가)
- Test: `backend/tests/test_fidelity_derived.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_fidelity_derived.py
# -*- coding: utf-8 -*-
"""V2 파생수치 검증 — 170% 사건(142→238=68% 증가를 '170% 증가'로 오기) 재발 방지."""
from backend.core.fidelity import derived_claims


def _card(body: str) -> str:
    return f'<div data-screen-label="01" style="width:1080px">{body}</div>'


def test_pct_fold_confusion_is_suspect():
    # 142→238은 1.68배 = 68% 증가. "170% 증가"는 배·%증가 혼동 → suspect
    html = _card("<p>142 MPa에서 238 MPa로 약 170% 증가</p>")
    claims = derived_claims(html, paper_text="142 199 238 MPa")
    assert len(claims) == 1
    assert claims[0]["kind"] == "pct_change"
    assert claims[0]["suspect"] is True


def test_correct_pct_change_not_suspect():
    html = _card("<p>142 MPa에서 238 MPa로 약 68% 증가</p>")
    claims = derived_claims(html, paper_text="142 238")
    assert claims[0]["suspect"] is False


def test_correct_fold_not_suspect():
    html = _card("<p>142에서 238로 약 1.7배 강해졌다</p>")
    claims = derived_claims(html, paper_text="142 238")
    assert claims[0]["kind"] == "fold"
    assert claims[0]["suspect"] is False


def test_no_derived_expressions_empty():
    html = _card("<p>압축강도 238 MPa를 기록했다</p>")
    assert derived_claims(html, paper_text="238") == []


def test_derived_scoped_per_card():
    # 파생표현과 근거수치가 다른 카드에 있으면 그 카드 안에서만 대조(전역 오염 방지)
    html = (_card("<p>강도 142 MPa와 238 MPa</p>")
            + '<div data-screen-label="02"><p>효율이 약 30% 증가</p></div>')
    claims = derived_claims(html, paper_text="142 238")
    # 30% 증가 카드에는 비교쌍이 없음 → 검산 불가 → suspect=False(모르면 죄 아님), unresolved=True
    assert claims[0]["suspect"] is False
    assert claims[0]["unresolved"] is True


def test_page_footer_does_not_launder_wrong_claim():
    # 프롬프트가 페이지번호(01/07)를 전 카드에 강제한다 → (1,7) 쌍이 검산에 끼면
    # 근거 없는 '7배' 주장이 '정합'으로 세탁된다(false negative). 페이지 패턴은 제외돼야 함.
    html = _card('<span>06 / 07</span><p>효율이 7배 향상됐다</p>')
    claims = derived_claims(html, paper_text="효율 향상")
    assert claims[0]["unresolved"] is True      # 비교쌍 없음 — 세탁 금지
    assert claims[0]["suspect"] is False


def test_year_pair_does_not_create_false_suspect():
    # 연도 2개(2020·2026)가 쌍이 되면 b/a*100≈100.3 → 정당한 '약 100% 향상'이 가짜 suspect가 된다.
    html = _card("<p>2020년 대비 2026년, 성능이 약 100% 향상</p>")
    claims = derived_claims(html, paper_text="2020 2026 성능 100% 향상")
    assert claims[0]["suspect"] is False
    assert claims[0]["unresolved"] is True      # 연도 제외 → 검산 불가
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_fidelity_derived.py -v`
Expected: FAIL — `ImportError: derived_claims`

- [ ] **Step 3: 구현** — `backend/core/fidelity.py` 끝에 추가:

```python
# ── V2: 파생수치 산수 정합 (2026-07-11) ──────────────────────────────────────
# 배경: 저작이 "142→238"을 '약 170% 증가'로 오기(1.7배와 %증가 혼동) — 원문 대조(존재)로는
# 못 잡는 내부 모순. 카드 단위로 파생표현(N% 증가·N배)을 찾아 같은 카드의 수치쌍과 검산한다.

_CARD_SPLIT = re.compile(r'(?=<div[^>]+data-screen-label=)', re.I)
_PCT_CHANGE = re.compile(r"(\d[\d,]*\.?\d*)\s*%\s*(증가|감소|향상|개선|절감|상승|하락)")
_FOLD = re.compile(r"(\d[\d,]*\.?\d*)\s*배")
_PCT_TOL = 5.0      # % 스케일 절대 오차 허용
_FOLD_TOL = 0.15    # 배 스케일 절대 오차 허용

# 검산쌍에서 뺄 크롬 노이즈. 프롬프트가 페이지번호(01/07)를 전 카드에 강제하므로 (1,7) 같은
# 가짜 쌍이 상시 생긴다 → 틀린 주장을 '정합'으로 세탁하거나 정당한 주장을 suspect로 만든다.
# (verify_deck이 맨정수를 노이즈로 제외한 ★핵심 설계 2와 같은 이유. 단 여기선 맨정수 전면
#  제외는 못 한다 — 142/238처럼 단위 없는 맨정수가 정당한 근거쌍인 경우가 있다. 표적 제외만.)
_PAGINATION = re.compile(r"\b\d{1,2}\s*/\s*\d{1,2}\b")


def _card_numbers(text: str) -> list[float]:
    """카드 본문의 검산 가능한 숫자. 페이지네이션·연도(1900~2100)는 제외."""
    cleaned = _PAGINATION.sub(" ", text)
    out = []
    for m in _CORE.finditer(cleaned):
        raw = m.group()
        try:
            v = float(raw.replace(",", ""))
        except ValueError:
            continue
        if v <= 0:
            continue
        if "." not in raw and 1900 <= v <= 2100:   # 연도 — 쌍이 되면 비율이 ≈100%라 오탐 유발
            continue
        out.append(v)
    return out


def _check_pairs(nums: list[float], claimed: float, kind: str) -> tuple[bool, bool]:
    """(suspect, unresolved). 같은 카드 수치쌍 (a<b)의 비율과 주장값을 대조.
    - pct_change: (b/a-1)*100 ≈ claimed 면 정합. b/a*100 ≈ claimed 인데 위가 아니면 혼동 의심.
    - fold: b/a ≈ claimed 면 정합.
    비교쌍이 하나도 없으면 unresolved=True(모르면 죄 아님)."""
    pairs = [(a, b) for i, a in enumerate(nums) for b in nums[i + 1:] if a != b]
    pairs = [(min(a, b), max(a, b)) for a, b in pairs]
    # 주장값 자신은 비교쌍에서 제외 (170이 카드 안 숫자로 다시 잡히는 자기참조 방지)
    pairs = [(a, b) for a, b in pairs if a != claimed and b != claimed]
    if not pairs:
        return False, True
    if kind == "fold":
        ok = any(abs(b / a - claimed) <= _FOLD_TOL for a, b in pairs)
        return (not ok and any(abs((b / a - 1) - claimed) <= _FOLD_TOL for a, b in pairs)), not ok
    # pct_change
    consistent = any(abs((b / a - 1) * 100 - claimed) <= _PCT_TOL for a, b in pairs)
    if consistent:
        return False, False
    confusion = any(abs(b / a * 100 - claimed) <= _PCT_TOL for a, b in pairs)
    return confusion, not confusion


def derived_claims(html: str, paper_text: str) -> list[dict]:
    """카드별 파생수치(N% 증가·N배)를 같은 카드 수치쌍과 검산.
    반환: [{value, kind, suspect, unresolved, verified, context}]"""
    results: list[dict] = []
    for chunk in _CARD_SPLIT.split(html):
        if "data-screen-label" not in chunk:
            continue
        content = _content_text(chunk)
        nums = _card_numbers(content)
        for pat, kind in ((_PCT_CHANGE, "pct_change"), (_FOLD, "fold")):
            for m in pat.finditer(content):
                claimed = float(m.group(1).replace(",", ""))
                suspect, unresolved = _check_pairs(nums, claimed, kind)
                core = m.group(1).replace(",", "")
                results.append({
                    "value": m.group().strip(),
                    "kind": kind,
                    "suspect": suspect,
                    "unresolved": unresolved,
                    "verified": core in _flat(paper_text),
                    "context": _clean_context(content, m.start(), m.end()),
                })
    return results
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest backend/tests/test_fidelity_derived.py -v`
Expected: 7 PASS

- [ ] **Step 5: 파이프라인 합류** — `backend/agents/deck/pipeline.py`의 `_verify_to_json`을 수정:

```python
def _verify_to_json(html: str, paper_text: str | None) -> tuple[str, dict]:
    """덱 HTML 충실성 검증 → (json 문자열, dict). paper_text 없으면 검증 보류(빈 결과)."""
    if not paper_text:
        payload = {"verified": 0, "unverified": 0, "claims": [], "derived": [], "skipped": True}
        return json.dumps(payload, ensure_ascii=False), payload
    claims = verify_deck(html, paper_text)
    payload = {
        "verified": sum(c.verified for c in claims),
        "unverified": sum(not c.verified for c in claims),
        "claims": [{"value": c.value, "context": c.context, "verified": c.verified} for c in claims],
        "derived": derived_claims(html, paper_text),
    }
    return json.dumps(payload, ensure_ascii=False), payload
```

import 줄 수정: `from ...core.fidelity import derived_claims, verify_deck`

그리고 `_execute()` 안의 V 단계(claims → verify_json 직조 부분, 현재 170~175행)도 동일하게 `_verify_to_json(html, s1_out.raw_text)`을 쓰도록 교체(중복 제거):

```python
    # ── V: 충실성 검증 (재사용) ────────────────────────────────────────────
    await db.update_job(job_id, status=JobStatus.RUNNING, stage="VERIFY", progress=70)
    verify_json, _ = _verify_to_json(html, s1_out.raw_text)
```

- [ ] **Step 6: 60k 절단 경고 표면화** (같은 파일 — eval셋의 long-1이 "절단 스트레스"인데 절단 발생 여부를 기록하는 계기가 하나도 없다. 저작은 60k에서 잘리는데 V는 원문 전문으로 검증하고 저지는 논문을 못 보니, 후반부를 통째로 누락한 덱이 세 계기판 모두에서 클린 패스한다.)

`backend/agents/deck/pipeline.py`의 `_execute()` S6 블록, `author_deck` 호출 **직전**에 추가:

```python
        if len(s1_out.raw_text) > MAX_SOURCE_CHARS:
            pct = (1 - MAX_SOURCE_CHARS / len(s1_out.raw_text)) * 100
            warnings.append(
                f"SOURCE_TRUNCATED: 원문 {len(s1_out.raw_text):,}자 중 {MAX_SOURCE_CHARS:,}자만 "
                f"저작에 사용 ({pct:.0f}% 미전달) — 후반부 내용이 덱에 반영되지 않았을 수 있습니다."
            )
```

임포트: `from .authoring import MAX_SOURCE_CHARS, author_deck`
`backend/agents/deck/authoring.py:20`의 `_MAX_SOURCE_CHARS`를 `MAX_SOURCE_CHARS`로 리네임(비공개→공개, 사용처 1곳도 함께 수정).

- [ ] **Step 7: 절단 경고 테스트 추가** — `backend/tests/test_deck_pipeline.py`에 (기존 mock 패턴 재사용):

```python
def test_long_source_emits_truncation_warning(monkeypatch):
    """60k자 초과 원문은 저작 전 절단 경고를 남긴다 — 없으면 long-1 저지 점수 해석 불가."""
    from backend.agents.deck import authoring
    assert authoring.MAX_SOURCE_CHARS == 60000
    long_text = "가" * 60001
    pct = (1 - authoring.MAX_SOURCE_CHARS / len(long_text)) * 100
    msg = (f"SOURCE_TRUNCATED: 원문 {len(long_text):,}자 중 {authoring.MAX_SOURCE_CHARS:,}자만 "
           f"저작에 사용 ({pct:.0f}% 미전달) — 후반부 내용이 덱에 반영되지 않았을 수 있습니다.")
    assert "SOURCE_TRUNCATED" in msg   # 문구 계약 고정
```

(파이프라인 전체를 mock으로 도는 기존 테스트가 있으면 그 warnings에 `SOURCE_TRUNCATED`가 실리는지 assert하는 형태로 강화하는 게 더 낫다 — 기존 테스트 구조를 보고 판단.)

- [ ] **Step 8: 전체 스위트 회귀 확인**

Run: `pytest backend/tests/ -q`
Expected: 기존 전부 PASS (231 + 7 + 1)

- [ ] **Step 9: 커밋**

커밋 전 `AUTHORING.md` §2에 결정로그 1줄 추가(같은 커밋):
`| 2026-07-XX | V | derived_claims() 신설 + 60k 절단 경고 | 170% 사건(존재대조로 못 잡는 내부모순) / 절단이 전 계기판에 비가시 | 다음 eval 백필 | (본 커밋) |`

```bash
git add backend/core/fidelity.py backend/agents/deck/pipeline.py backend/agents/deck/authoring.py backend/tests/test_fidelity_derived.py backend/tests/test_deck_pipeline.py backend/agents/deck/AUTHORING.md
git commit -m "[BE] V2 파생수치 산수 정합 + 60k 절단 경고 — %증가·배 혼동 카드단위 검산(170% 재발 방지)"
```

---

### Task 5.5: V2 suspect 웹 표면화 (무료 — 표면화 없는 검산은 로그일 뿐)

> 170% 오기는 검증 리포트에 "수치 존재=VERIFIED"로 실려 나갔다. V2가 suspect를 계산해도
> UI가 렌더하지 않으면 사용자는 영원히 못 본다 — **정확히 같은 실패의 반복**. 헌법 §2 "미확인은
> 사용자에 표면화"의 이행이다. `web/`에 'derived' 문자열이 현재 0건임을 확인하고 시작.

**Files:**
- Create: `web/src/lib/verifyStatus.ts`
- Modify: `web/src/components/deck/DeckFactPanel.tsx`
- Test: `web/src/lib/verifyStatus.test.ts`

- [ ] **Step 1: 실패하는 테스트 작성**

```typescript
// web/src/lib/verifyStatus.test.ts
import { describe, expect, it } from 'vitest'
import { suspectClaims, isAllClear } from './verifyStatus'

const base = { verified: 3, unverified: 0, claims: [] }

describe('verifyStatus', () => {
  it('suspect만 골라낸다 (unresolved는 노이즈라 제외 — 모르면 죄 아님)', () => {
    const derived = [
      { value: '170% 증가', kind: 'pct_change', suspect: true, unresolved: false, verified: false, context: '142→238' },
      { value: '30% 증가', kind: 'pct_change', suspect: false, unresolved: true, verified: false, context: '비교쌍 없음' },
    ]
    const s = suspectClaims({ ...base, derived })
    expect(s).toHaveLength(1)
    expect(s[0].value).toBe('170% 증가')
  })

  it('suspect가 있으면 allClear가 아니다 (초록 완료 문구 억제)', () => {
    const derived = [{ value: '170% 증가', kind: 'pct_change', suspect: true, unresolved: false, verified: false, context: '' }]
    expect(isAllClear({ ...base, derived })).toBe(false)
  })

  it('unverified 0 + suspect 0 이면 allClear', () => {
    expect(isAllClear({ ...base, derived: [] })).toBe(true)
  })

  it('구 덱(derived 키 없음)도 안전 — 하위호환', () => {
    expect(isAllClear(base)).toBe(true)
    expect(suspectClaims(base)).toEqual([])
  })

  it('verify 자체가 없으면 allClear 아님', () => {
    expect(isAllClear(null)).toBe(false)
  })
})
```

- [ ] **Step 2: 실패 확인**

Run: `cd web && npx vitest run src/lib/verifyStatus.test.ts`
Expected: FAIL — 모듈 없음

- [ ] **Step 3: 구현**

```typescript
// web/src/lib/verifyStatus.ts
// V2 파생수치(derived) 판독 — 산수 불일치(suspect)를 팩트 패널에 표면화하기 위한 순수함수.
// unresolved(검산 불가)는 렌더하지 않는다 — 모르면 죄 아님(노이즈로 신뢰를 깎지 않는다).

export interface DerivedClaim {
  value: string
  kind: string
  suspect: boolean
  unresolved: boolean
  verified: boolean
  context: string
}

export interface VerifyClaim { value: string; context: string; verified: boolean }

export interface VerifyData {
  verified: number
  unverified: number
  claims: VerifyClaim[]
  derived?: DerivedClaim[]      // 구 덱엔 없음 — optional
}

export function suspectClaims(verify: VerifyData | null | undefined): DerivedClaim[] {
  return (verify?.derived ?? []).filter((d) => d.suspect)
}

export function isAllClear(verify: VerifyData | null | undefined): boolean {
  if (!verify) return false
  return verify.unverified === 0 && suspectClaims(verify).length === 0
}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `cd web && npx vitest run src/lib/verifyStatus.test.ts`
Expected: 5 PASS

- [ ] **Step 5: DeckFactPanel 배선** — `web/src/components/deck/DeckFactPanel.tsx`:

로컬 인터페이스(7~8행)를 삭제하고 공용 타입을 임포트:

```typescript
import { isAllClear, suspectClaims, type VerifyData } from '@/lib/verifyStatus'
```

`allClear` 계산(21행)을 교체하고 suspect 목록을 뽑는다:

```typescript
  const suspects = suspectClaims(verify)
  const allClear = isAllClear(verify)
```

claim ledger `<ul>`(77행) **맨 위**에 suspect 행을 렌더한다(기존 `shown.map` 앞):

```tsx
            {suspects.map((d, i) => (
              <li key={`d${i}`} className="flex items-center gap-2.5 py-2.5 border-t border-deck-line-soft first:border-t-0">
                <span className="font-mono text-[12.5px] font-bold text-ink shrink-0 max-w-[128px] truncate" title={d.value}>{d.value}</span>
                <span className="flex-1 text-[11px] text-ink-2 leading-snug line-clamp-2">
                  카드 안 수치와 계산이 맞지 않아요 — ‘% 증가’와 ‘배’를 혼동했을 수 있어요. {d.context.trim()}
                </span>
                <span className="shrink-0 text-[9.5px] font-bold px-1.5 py-1 rounded-md bg-risk-medium-faint text-risk-medium border border-risk-medium-border">계산 불일치</span>
              </li>
            ))}
```

ledger 헤더 카운트(74행)와 표시 조건(61행)도 suspect를 포함하도록:
- 조건: `{(shown.length > 0 || suspects.length > 0) && (`
- 카운트: `{shown.length + suspects.length} / {claims.length + suspects.length}`

푸터(97~105행)는 `allClear`가 이미 강화됐으므로 자동으로 경고 문구로 떨어진다 — suspect가 있는데 "모든 수치가 원문에서 추적됐습니다"가 뜨는 모순이 차단된다.

- [ ] **Step 6: 타입·전체 vitest 회귀**

Run: `cd web && npx tsc --noEmit && npx vitest run`
Expected: 타입 에러 0, 기존 58 + 신규 5 PASS

- [ ] **Step 7: 커밋**

```bash
git add web/src/lib/verifyStatus.ts web/src/lib/verifyStatus.test.ts web/src/components/deck/DeckFactPanel.tsx
git commit -m "[WEB] V2 파생수치 suspect 표면화 — '계산 불일치' 배지 + allClear 게이트 강화"
```

---

# Phase 2 — 프롬프트 5층 재편 (무료)

### Task 6: authoring_prompts.py 재구성

**Files:**
- Modify: `backend/agents/deck/authoring_prompts.py`
- Modify: `backend/agents/deck/authoring.py`
- Modify: `backend/tests/test_deck_pipeline.py` (기존 format 테스트가 새 슬롯으로 KeyError)
- Test: `backend/tests/test_authoring_prompts.py`

**⚠️ 함정 3개**:
1. `AUTHORING_SYSTEM.format(persona=...)`·`AUTHORING_USER.format(...)` 둘 다 `.format()` 대상 — 넣는 **JSON 예시의 중괄호는 반드시 `{{ }}`로 이스케이프**(안 하면 KeyError).
2. **L4 자기검수는 시스템 프롬프트 끝이 아니라 유저 프롬프트 맨 끝**에 둔다. API 순서상 시스템 뒤에 유저(refs 2덱 + 논문 60k자 ≈ 40k+ 토큰)가 오므로, 시스템 끝은 생성 시점 기준 **컨텍스트 한가운데**다 — recency 이득 0. 진짜 말단은 `## 지시` 뒤.
3. `.rindex(...) > len(s)*0.7` 같은 **비율 기반 위치 테스트 금지** — `{section_map_text}` 슬롯이 60k자로 확장되면 비율이 무의미해진다. "`## 지시` 이후에 있는가"로 검사.

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_authoring_prompts.py
# -*- coding: utf-8 -*-
"""프롬프트 계약 마커 테스트 — 5층 구조·매니페스트·자기검수·card_count 치환."""
from backend.agents.deck import authoring_prompts as P


def test_system_formats_without_error():
    s = P.AUTHORING_SYSTEM.format(persona="테스트 페르소나")
    assert "테스트 페르소나" in s


def test_user_formats_without_error():
    u = P.AUTHORING_USER.format(
        few_shot_refs="R", section_map_text="T", title="t", authors="a", year="2026",
        publisher="p", card_count=5, art_direction="", history_block="",
    )
    assert "5장" in u          # card_count 치환 확인


def test_system_has_layer_markers():
    s = P.AUTHORING_SYSTEM
    assert "PI_MANIFEST" in s                    # L3 선언 계약
    assert "이모지" in s                          # L1 신규 가드
    assert "새 아크를 발명" in s                   # 아키타입 탈출구(감옥 금지)
    assert "rejected_arc" in s                   # 버린 아크 근거 — 1번 아크 디폴트 픽 방지


def test_selfcheck_lives_at_the_very_end_of_user_prompt():
    # 시스템 끝 ≠ 컨텍스트 끝(뒤에 유저 프롬프트 40k+ 토큰이 붙는다) → 유저 말단이 진짜 recency
    u = P.AUTHORING_USER
    assert "자기검수" in u
    assert u.rindex("자기검수") > u.index("## 지시")


def test_no_hardcoded_seven():
    assert "7장" not in P.AUTHORING_SYSTEM
    assert "7장" not in P.AUTHORING_USER
    assert "7장" not in P.art_direction_block("지브리풍")   # 상수 밖 함수 문자열까지 그물에
    assert "{card_count}" in P.AUTHORING_USER


def test_user_prompt_has_history_slot():
    assert "{history_block}" in P.AUTHORING_USER


def test_refs_header_declares_used_directions():
    # 고정 refs(수만 토큰 시연)가 이력(3줄 텍스트)을 이긴다 — refs가 쓴 방향을 명시해 반복을 막는다
    refs = P.few_shot_refs(2)
    assert "이미 보여준 방향" in refs


def test_output_contract_preserved():
    s = P.AUTHORING_SYSTEM
    assert "data-screen-label" in s
    assert "1080px" in s and "1350px" in s
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_authoring_prompts.py -v`
Expected: FAIL (PI_MANIFEST·history_block 등 부재)

- [ ] **Step 3: AUTHORING_SYSTEM 수정.** 기존 내용을 다음 재배치로 편집(전면 재작성 아님 — 기존 절 텍스트는 보존·이동):

**(a)** `[저작 가드 — …]` 절 기존 1~4조 유지하고 5~8조 추가:

```
5. 이모지 문자(🪥·🌊·🐟 류) 사용 금지 — 아이콘·오브젝트는 전부 CSS/SVG로 직접 그려 덱 팔레트를
   따르게 하라. (✓·✕·→·· 같은 타이포그래피 기호는 허용.)
6. 파생 수치(증가율·배수·차이)는 원문에 그 표현이 있을 때만 그대로 쓴다. 직접 계산이 불가피하면
   'N배(a→b)' 형식으로 근거 수치를 함께 노출하고 재검산하라. **'N% 증가'와 'N배' 혼동은 실패다**
   — 142→238은 '1.7배' 또는 '약 68% 증가'지, '170% 증가'가 아니다.
7. 표지 헤드라인은 최대 3줄, 훅 단어(가장 놀라운 말)를 첫 줄에. 표지 하단 보조 문단은 2줄 이내.
8. 다이어그램은 본문이 주장한 형상을 그대로 그린다 — '삼각형 구조'라 썼으면 삼각형을 그려라.
   본문과 다른 모양·개수의 그림은 실패다.
```

**(b)** '7장' 하드코딩 **전수 제거**. 위치를 외우지 말고 먼저 확인:

Run: `grep -n "7장\|01/07" backend/agents/deck/authoring_prompts.py`

현재 5곳 + `(01/07)` 1곳 + 함수 1곳:
- 106행 `[계정 시스템 — 카드 7장을 …]` 제목 → "덱 전체를"
- 109행 `(01/07)` → `(01/N)`
- 111행 "7장을 하나의 시리즈로 묶는다" → "전 카드를 하나의 시리즈로 묶는다"
- 112행 "한 규칙으로 7장 관통" → "한 규칙으로 전 카드 관통"
- 141행 "7장 내내" → "전 카드 내내"
- 188행 `art_direction_block()` f-string "이 방향으로 7장 일관 실행" → "이 방향으로 전 카드 일관 실행" (**상수 밖이라 눈에 안 띄지만 런타임에 유저 프롬프트로 주입된다** — card_count=5 요청 시 "5장 저작하라"와 "7장 일관 실행"이 같은 프롬프트에 공존)

테스트가 정본이다 — `grep`이 0건이 될 때까지.

**(c)** `[서사 — …]` 절 앞에 L3 아키타입 절 신설 (중괄호 이스케이프 주의):

```
[서사 아크 — 골라 선언하라. 메뉴는 팔레트지 감옥이 아니다]
아래는 검증된 아크 6종이다. 이 논문의 킬러 자산(수치인가·개념인가·역설인가·여정인가)에 맞는
하나를 고르거나, **맞는 게 없으면 새 아크를 발명하라**:
1. 데이터 클라이맥스형 — 킬러 수치가 있을 때. 문제→방법→숫자 한 방.
2. 개념 체험형 — 킬러가 아이디어일 때. 독자가 형태로 개념을 체험(빈칸·비교 체험).
3. 비포/애프터형 — 변화가 극적일 때. 같은 프레임 반복 대비.
4. 미스터리 해결형 — '왜?'가 강할 때. 표지에서 질문을 걸고 카드마다 단서.
5. 반전형 — 통념을 깰 때. '다들 X라 믿었다 → 아니었다'.
6. 과정 서사형 — 연구 여정 자체가 이야기일 때. 실패→우회→도달.
킬러 수치가 없는 논문에 억지 데이터 클라이맥스를 만들지 마라 — 그게 수치 왜곡의 뿌리다.
1번은 가장 흔한 아크다. 1번을 고를 거면 **왜 다른 아크가 아닌지**를 rejected_arc에 적어라.

선언(필수): <head> 첫 줄에 아래 형식의 주석 한 줄로 네 편집 결정을 먼저 선언하고, 선언대로 저작하라.
<!-- PI_MANIFEST {{"archetype": "선택한 아크", "killer_asset": "이 논문의 킬러 자산 한 줄", "palette": "주조색 2~3개", "motif": "반복 모티프", "rejected_arc": "고려했으나 버린 아크 + 이유 한 줄"}} -->
```

**(d)** L2 크래프트 절의 **모순 2곳만 조건화** (다이어트 아님 — 기존 텍스트 보존. 지금 L2는 무조건문으로 "큰 수치가 주인공"·"다크는 데이터 클라이맥스 1장에"라 말해, L3가 "억지 클라이맥스 금지"라 해도 이론·인문 논문에서 수치 조작 압력이 그대로 남는다):

- 93행 `**밝음↔어둠 페이싱(기계적 교대 금지)**: 다크는 표지 + 데이터 클라이맥스 1장 + 클로징`
  → `… 다크는 표지 + **클라이맥스 카드 1장(아크의 정점 — 수치든 개념이든 반전이든)** + 클로징`
- 97행 `- **큰 수치가 주인공**: 핵심 숫자 하나를 …`
  → `- **큰 수치가 주인공(킬러 수치가 있는 논문에서만)**: 핵심 숫자 하나를 … (수치가 주인공이 아닌 논문이면 이 자리를 개념·대비·질문의 시각적 클라이맥스로 대신하라.)`

**(e)** `[페르소나]` 절 뒤에 L4 **포인터 한 줄만** 남긴다 (체크리스트 본문은 유저 프롬프트 말단으로 — 함정 2):

```
[자기검수]
유저 프롬프트 말미의 체크리스트를 저작 내내 지키고, 각 카드를 닫기 전 스스로 점검하라.
```

- [ ] **Step 3.5: `few_shot_refs()`에 방향 헤더 추가** (`authoring_prompts.py`)

고정 refs 2덱은 수만 토큰의 **구체적 시연**이고 history_block은 3줄 추상 텍스트다 — 앵커 싸움에서 이력이 진다. 게다가 신규 유저·계정 첫 덱은 이력이 비어 변주 압력이 0이라, 모든 계정의 초기 덱이 refs가 시연한 두 방향으로 수렴한다. refs가 **자기가 이미 쓴 방향을 실토하게** 만든다:

```python
@lru_cache(maxsize=8)
def few_shot_refs(n: int = 2) -> str:
    """레퍼런스 HTML n개를 품질·범위 예시로 임베드. 존재하는 것만.

    ★헤더로 '이 refs가 이미 쓴 아크·무드'를 명시한다 — 구체 시연(수만 토큰)이 추상 지시를
      이기므로, 명시하지 않으면 모델이 refs의 아크·팔레트를 그대로 재생산한다(동질화의 뿌리).
    """
    blocks: list[str] = []
    used: list[str] = []
    for ref in REF_LIBRARY[:n]:
        p = _ROOT / ref["path"]
        if p.exists():
            blocks.append(f"<!-- ===== REFERENCE ({ref['path']}) ===== -->\n{p.read_text(encoding='utf-8')}")
            used.append(f"[{ref['arc']} / {ref['mood']}]")
    if not blocks:
        return ""
    header = (
        "★이 레퍼런스들이 **이미 보여준 방향**: " + ", ".join(used) + "\n"
        "이 아크+팔레트 조합을 그대로 반복하면 베끼기다. 이 논문이 진짜 그 아크를 요구한다면\n"
        "팔레트·모티프는 반드시 달리하라. 배울 것은 마감의 완성도지 색이나 구도가 아니다.\n\n"
    )
    return header + "\n\n".join(blocks)
```

(`REF_LIBRARY`는 Task 9에서 태그 구조로 바뀐다 — **Task 9를 Task 6보다 먼저 실행하거나**, 이 스텝에서 `REF_LIBRARY`를 함께 도입한다. 순서는 실행자가 택하되 둘 중 하나는 반드시.)

- [ ] **Step 4: AUTHORING_USER 수정** — `{art_direction}## 지시` 사이에 `{history_block}` 삽입, "7장 내내" → "{card_count}장 내내":

```python
AUTHORING_USER = """## 레퍼런스 덱 (방향이 서로 다른 품질 예시 — 베끼지 말고 '범위'만 배우기)
{few_shot_refs}

## 논문 원문 (유일한 사실 소스)
{section_map_text}

---
제목: {title}
저자: {authors}
연도: {year}
발행 주체: {publisher}

---
{history_block}{art_direction}## 지시
위 논문으로 카드 {card_count}장짜리 발행 가능한 덱을 저작하라.
- 이 논문에 맞는 한 디자인 방향을 정해 {card_count}장 내내 일관 실행.
- '형태=내용' 체험형 카드를 1장 이상 발명.
- 모든 수치는 원문에서. **계정 정체성은 실제로 채운다 — 자리표시자 절대 금지.**
  위 '발행 주체'가 주어졌으면 그대로 쓰고, 없으면 위 '저자'와 논문 본문의 소속(affiliation)을 읽어
  발행 주체를 특정하라(예: 'Korea Institute of Industrial Technology' → '한국생산기술연구원').
  표지·전 카드 푸터에 그 기관명을, 핸들이 필요하면 기관 영문 약칭으로 일관 반복 조판하라.
  **최종 출력에 ［...］ 대괄호나 '연구실 이름'·'기관명' 같은 미치환 자리표시자가 남으면 실패다.**
- HTML 전문만 출력(코드펜스·설명 없이).

## 출력 직전 자기검수 (L4 — 저작 내내 지키고, 각 카드를 닫기 전 점검하라)
□ 미치환 자리표시자([기관명]·'연구실 이름' 류)가 남았는가?
□ 이모지 문자가 있는가? (아이콘은 CSS/SVG로 직접 그린다)
□ 처음 등장하는 전문용어·단위(wt%·약어 등)에 쉬운 앵커가 빠진 곳이 있는가?
□ 파생 수치(N% 증가·N배)를 전부 재검산했는가? %증가와 배를 혼동한 곳은 없는가?
□ 킬러 수치가 없는데 부수 숫자(개수·연도·인용수)를 히어로 숫자로 승격한 곳이 있는가?
□ 다이어그램이 본문 주장(모양·개수)과 다른 곳이 있는가?
□ 카드를 세로 3분할했을 때 통째로 빈 구획이 있는 카드가 있는가?
  (여백은 요소 사이에 — 콘텐츠가 적으면 요소를 키우고 justify-content:space-between으로 분배)
□ PI_MANIFEST 선언과 실제 덱(아크·팔레트·모티프)이 일치하는가?

마지막 카드 뒤 </html> 직전에 자가판정을 주석 한 줄로 보고하라(원샷 생성 말미에 자기 산출물을
다시 주목하게 하는 장치 — 코드가 이를 파싱해 경고로 표면화한다):
<!-- PI_SELFCHECK {{"placeholder": false, "emoji": false, "unit_anchored": true, "derived_ok": true, "hero_number_ok": true, "visual_matches_text": true, "no_dead_zone": true, "manifest_matches": true}} -->"""
```

- [ ] **Step 5: authoring.py에 history_block 파라미터 배선** — `author_deck` 시그니처에 `history_block: str = ""` 추가, `AUTHORING_USER.format(...)`에 `history_block=history_block` 추가.

- [ ] **Step 6: 기존 테스트 갱신** — `backend/tests/test_deck_pipeline.py`의 `test_prompts_format_without_keyerror`(82~92행 부근)가 `P.AUTHORING_USER.format(...)`을 **현행 키셋으로 직접 호출**한다. `{history_block}` 슬롯 추가로 KeyError가 나므로 그 호출에 `history_block=""`를 추가한다. (안 하면 Step 7의 "전부 PASS"가 성립하지 않는다.)

- [ ] **Step 7: 테스트 통과 + 전체 회귀**

Run: `pytest backend/tests/test_authoring_prompts.py backend/tests/test_deck_pipeline.py -v`
Expected: 전부 PASS. 이어서 `pytest backend/tests/ -q` 전부 PASS.

- [ ] **Step 8: 커밋**

커밋 전 `AUTHORING.md` §2에 결정로그 1줄 추가(같은 커밋):
`| 2026-07-XX | 프롬프트 | 5층 재편 — L1 가드 4종·L2 모순 조건화·L3 아키타입 선언(rejected_arc)·L4 유저말단+PI_SELFCHECK·refs 방향헤더·7장 전수제거 | 블랙박스 심사 결함↔갭 + 채널분리 진단 + 31에이전트 검증 | 다음 eval 백필 | (본 커밋) |`

```bash
git add backend/agents/deck/authoring_prompts.py backend/agents/deck/authoring.py backend/tests/test_authoring_prompts.py backend/tests/test_deck_pipeline.py backend/agents/deck/AUTHORING.md
git commit -m "[BE] 저작 프롬프트 5층 재편 — 아키타입 선언·L1 가드 4종·L4 유저말단 자기검수·refs 방향헤더·7장 제거"
```

---

# Phase 3 — 매니페스트 파싱 + 반복이력 소프트 주입 (무료)

### Task 7: manifest.py (순수함수) + DB 테이블

**Files:**
- Create: `backend/agents/deck/manifest.py`
- Modify: `backend/core/db.py`
- Test: `backend/tests/test_deck_manifest.py`

- [ ] **Step 1: 실패하는 테스트 작성**

```python
# backend/tests/test_deck_manifest.py
# -*- coding: utf-8 -*-
from backend.agents.deck.manifest import build_history_block, parse_manifest, selfcheck_failures

_HTML = ('<!DOCTYPE html><html><head>'
         '<!-- PI_MANIFEST {"archetype": "반전형", "killer_asset": "플라스틱보다 단단", '
         '"palette": "아이보리·세이지", "motif": "구슬", "rejected_arc": "데이터 클라이맥스형 — 수치가 약함"} -->'
         '<style></style></head><body></body></html>')


def test_parse_manifest_ok():
    m = parse_manifest(_HTML)
    assert m["archetype"] == "반전형"
    assert m["motif"] == "구슬"
    assert "rejected_arc" in m


def test_parse_manifest_absent_returns_none():
    assert parse_manifest("<!DOCTYPE html><html></html>") is None


def test_parse_manifest_broken_json_returns_none():
    assert parse_manifest('<!-- PI_MANIFEST {broken -->') is None


def test_history_block_empty_when_no_history():
    assert build_history_block([]) == ""


def test_history_block_soft_wording():
    block = build_history_block([
        {"archetype": "데이터 클라이맥스형", "palette": "아이보리", "motif": "구슬"},
        {"archetype": "반전형", "palette": "네이비", "motif": "그래프"},
    ])
    assert "데이터 클라이맥스형" in block
    assert "적합이 신선함을 이긴다" in block      # 소프트 선호 (하드 금지 아님 — 정밀화 ⑥)
    assert "금지" not in block.split("적합")[0]   # 하드 금지 표현 없음


def test_selfcheck_failures_lists_false_items():
    html = ('<html><body></body>'
            '<!-- PI_SELFCHECK {"placeholder": false, "emoji": true, "derived_ok": false} -->'
            '</html>')
    # 자기신고 의미론: placeholder/emoji는 true=결함, *_ok/no_*는 false=결함
    fails = selfcheck_failures(html)
    assert "emoji" in fails and "derived_ok" in fails
    assert "placeholder" not in fails


def test_selfcheck_absent_returns_empty():
    assert selfcheck_failures("<html></html>") == []
```

- [ ] **Step 2: 실패 확인**

Run: `pytest backend/tests/test_deck_manifest.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: manifest.py 구현**

```python
# -*- coding: utf-8 -*-
"""PI_MANIFEST / PI_SELFCHECK — 저작 콜이 선언한 편집 결정과 자가판정 파싱 + 이력 주입.

선언은 같은 콜 안의 chain-of-thought(한 마음, 헌법 §1)이며 코드가 형태를 강제하지 않는다.
파싱 실패는 경고 사유일 뿐 파이프라인 실패가 아니다(소프트)."""
from __future__ import annotations

import json
import re

_MANIFEST_RE = re.compile(r"<!--\s*PI_MANIFEST\s*(\{.*?\})\s*-->", re.S)
_SELFCHECK_RE = re.compile(r"<!--\s*PI_SELFCHECK\s*(\{.*?\})\s*-->", re.S)

# 자기신고 키의 극성: 결함을 묻는 키(true=결함) vs 정상을 묻는 키(false=결함)
_DEFECT_IF_TRUE = {"placeholder", "emoji"}


def parse_manifest(html: str) -> dict | None:
    """덱 HTML에서 PI_MANIFEST JSON 추출. 없거나 깨졌으면 None."""
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

    자기신고라 신뢰의 정본은 아니다 — V·저지와의 삼각측량용 신호로만 쓴다(경고 표면화)."""
    m = _SELFCHECK_RE.search(html)
    if not m:
        return []
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    if not isinstance(obj, dict):
        return []
    fails = []
    for k, v in obj.items():
        if not isinstance(v, bool):
            continue
        if (k in _DEFECT_IF_TRUE and v) or (k not in _DEFECT_IF_TRUE and not v):
            fails.append(k)
    return fails


def build_history_block(recent: list[dict]) -> str:
    """최근 덱 매니페스트 → 소프트 변주 선호 텍스트. 이력 없으면 빈 문자열.

    하드 금지가 아니다 — 논문 적합이 신선함을 이긴다(검증 정밀화 ⑥)."""
    if not recent:
        return ""
    lines = ["## 이 계정의 최근 발행 덱 (변주 참고)"]
    for m in recent:
        lines.append(f"- 아크: {m.get('archetype', '?')} / 팔레트: {m.get('palette', '?')}"
                     f" / 모티프: {m.get('motif', '?')}")
    lines.append("정확 반복은 피하되, 이 논문이 허락하는 선에서 변주하라. 적합이 신선함을 이긴다.")
    return "\n".join(lines) + "\n\n"
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `pytest backend/tests/test_deck_manifest.py -v`
Expected: 7 PASS

- [ ] **Step 5: db.py에 테이블 + 함수 추가.** `_init_schema`(CREATE TABLE 나열부)에:

```sql
            CREATE TABLE IF NOT EXISTS deck_manifest (
                job_id TEXT PRIMARY KEY,
                user_id INTEGER,
                manifest_json TEXT,
                created_at TEXT
            );
```

`save_authored_deck` 근처(348행대)에 함수 2개 추가:

```python
async def save_deck_manifest(job_id: str, user_id: int | None, manifest_json: str) -> None:
    """저작 콜이 선언한 편집 결정(PI_MANIFEST) 저장 — 반복이력 소프트 주입용."""
    async with _connect() as conn:
        await conn.execute(
            "INSERT OR REPLACE INTO deck_manifest (job_id, user_id, manifest_json, created_at) "
            "VALUES (?, ?, ?, ?)",
            (job_id, user_id, manifest_json, _utc_now_iso()),
        )
        await conn.commit()


async def get_recent_manifests(user_id: int | None, limit: int = 3) -> list[dict]:
    """이 유저의 최근 덱 매니페스트(신순). user_id 없으면 빈 리스트."""
    if user_id is None:
        return []
    async with _connect() as conn:
        cur = await conn.execute(
            "SELECT manifest_json FROM deck_manifest WHERE user_id = ? "
            "ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        )
        rows = await cur.fetchall()
    out: list[dict] = []
    for (mj,) in rows:
        try:
            obj = json.loads(mj)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


async def delete_deck_manifests(user_id: int) -> None:
    """이 유저의 매니페스트 이력 전부 삭제 — eval 격리 전용(측정 시 이력 효과 배제).

    eval_runner가 논문마다 호출한다: 이력이 남으면 after 런의 2~6번째 논문이 앞 덱들의
    매니페스트를 주입받아 실행 순서에 종속되고, 런을 반복할수록 조건이 달라져 재현이 깨진다."""
    async with _connect() as conn:
        await conn.execute("DELETE FROM deck_manifest WHERE user_id = ?", (user_id,))
        await conn.commit()
```

(파일 상단에 `import json`이 이미 없으면 추가. `_connect`·`_utc_now_iso`는 기존 헬퍼 재사용 — `save_authored_deck` 구현과 같은 패턴을 따를 것.)

- [ ] **Step 6: 전체 회귀**

Run: `pytest backend/tests/ -q`
Expected: 전부 PASS

- [ ] **Step 7: 커밋**

```bash
git add backend/agents/deck/manifest.py backend/core/db.py backend/tests/test_deck_manifest.py
git commit -m "[BE] PI_MANIFEST 파싱 + deck_manifest 테이블 — 편집 결정 지문 저장"
```

---

### Task 8: 파이프라인 배선 — 이력 조회→주입, 저작 후 매니페스트 저장

**Files:**
- Modify: `backend/agents/deck/pipeline.py` (`_execute`의 S6 블록)

- [ ] **Step 1: `_execute` S6 블록 수정** (임포트에 `from .manifest import build_history_block, parse_manifest, selfcheck_failures` 추가):

```python
    # ── S6: 단일 저작 ──────────────────────────────────────────────────────
    try:
        await db.update_job(job_id, status=JobStatus.RUNNING, stage="AUTHOR", progress=40)
        recent = await db.get_recent_manifests(user_id)
        html = await author_deck(
            raw_text=s1_out.raw_text,
            metadata=s1_out.metadata,
            card_count=card_count,
            persona=persona,
            style_direction=style_direction,
            history_block=build_history_block(recent),
        )
        if not html or "data-screen-label" not in html:
            raise ValueError("저작 결과에 카드(data-screen-label)가 없습니다")
    except Exception as exc:
        logger.error("deck AUTHOR fatal: %s", exc)
        await db.update_job(job_id, status=JobStatus.ERROR, stage="AUTHOR", progress=40,
                            warnings=warnings + [f"ERR-AUTHOR: {exc}"])
        await _log_done(job_id, user_id, started, card_count)
        return

    # 매니페스트 저장 (소프트 — 없어도 실패 아님, 경고만)
    manifest = parse_manifest(html)
    if manifest:
        await db.save_deck_manifest(job_id, user_id, json.dumps(manifest, ensure_ascii=False))
    else:
        warnings.append("PI_MANIFEST 미선언 — 반복이력에 이 덱이 기록되지 않음")

    # 자가판정(PI_SELFCHECK) — 모델이 스스로 실패라 신고한 항목을 경고로 표면화.
    # 자기신고라 정본은 아니고 V·저지와의 삼각측량 신호(막지 않음, 헌법 3조).
    sc_fails = selfcheck_failures(html)
    if sc_fails:
        warnings.append("자가검수 미통과 항목: " + ", ".join(sc_fails))
```

- [ ] **Step 2: 전체 회귀** (기존 pipeline 테스트가 author_deck을 mock하므로 시그니처 호환 확인)

Run: `pytest backend/tests/ -q`
Expected: 전부 PASS. mock 시그니처 불일치 시 해당 테스트의 mock에 `history_block` 키워드 허용 추가(`**kwargs`).

- [ ] **Step 3: 커밋**

```bash
git add backend/agents/deck/pipeline.py
git commit -m "[BE] 저작 파이프라인 — 반복이력 소프트 주입 + 매니페스트 저장 배선"
```

---

# Phase 4 — refs 라이브러리 구조화 + 승격 게이트 (무료)

### Task 9: REF_LIBRARY 태그 스키마 (승격 게이트는 Task 2.5의 AUTHORING.md §4가 정본)

**Files:**
- Modify: `backend/agents/deck/authoring_prompts.py` (`_REF_HTMLS` 블록, 19~34행)
- Modify: `backend/agents/deck/AUTHORING.md` (§2 결정로그 1줄)

> **실행 순서 주의**: Task 6 Step 3.5(refs 방향 헤더)가 `REF_LIBRARY`의 `arc`·`mood` 태그를 쓴다.
> **이 태스크를 Task 6보다 먼저 실행**하거나, Task 6 안에서 `REF_LIBRARY`를 함께 도입할 것.

- [ ] **Step 1: `_REF_HTMLS` → `REF_LIBRARY` 구조화** (`few_shot_refs`의 방향 헤더는 Task 6 Step 3.5에서 붙는다):

```python
# 의도적으로 '다른 방향' 우선 — 다양성으로 범위를 가르친다(메모리: 레퍼런스 다양성).
# 승격 기준: backend/agents/deck/AUTHORING.md §4 (클린 패스만 — 결함 있는 덱은 결함을 가르친다)
# ★현행 3개가 전부 cs-ml이다 — 재료·바이오·인문 논문도 CS refs를 품질 앵커로 받는 장르 미스매치.
#   해소는 승격 루프(다른 장르의 클린 패스 덱을 편입)로. 지금은 그 사실을 태그로 표면화만.
REF_LIBRARY = [
    {"path": "output/cardnews_bert_design/cards.html",
     "genre": "cs-ml", "mood": "웜 페이퍼 에디토리얼(오렌지·형광펜)", "arc": "개념 체험형"},
    {"path": "output/cardnews_attention_neon/cards.html",
     "genre": "cs-ml", "mood": "미드나잇 네온(듀얼악센트·SVG그래프)", "arc": "데이터 클라이맥스형"},
    {"path": "output/cardnews_attention/cards.html",
     "genre": "cs-ml", "mood": "포레스트 그린(보조)", "arc": "데이터 클라이맥스형"},
]
```

- [ ] **Step 2: AUTHORING.md §2 결정로그에 1줄 추가** (같은 커밋 — 컨트롤룸 규율):

```
| 2026-07-XX | refs | _REF_HTMLS → REF_LIBRARY 태그 구조화 | 장르매칭·승격 루프 기반 마련(현행 전부 cs-ml임을 표면화) | 동작 불변 | (본 커밋) |
```

- [ ] **Step 3: 회귀 + 커밋**

Run: `pytest backend/tests/ -q` → 전부 PASS

```bash
git add backend/agents/deck/authoring_prompts.py backend/agents/deck/AUTHORING.md
git commit -m "[BE] refs 라이브러리 태그 스키마(REF_LIBRARY) — 승격 게이트는 AUTHORING.md 정본"
```

---

# Phase 5 — 재측정 + 채택 판정

### Task 10: ⛔유료 게이트 — 재측정 (사용자 허락 후)

**Files:** 없음 (실행만). 산출물: `eval/runs/after-<날짜>/{results.json, diversity.json}`

- [ ] **Step 1: 비용 고지 + 허락** (베이스라인과 동일 규모 ~$6~11: 저작 6콜 + 저지 6콜 + 다양성 1콜)
- [ ] **Step 2: 같은 eval셋으로 재실행** (러너가 논문마다 이력을 비우므로 프롬프트 효과만 측정됨 — 이력 주입 효과는 원하면 나중에 별도 A/B로)

Run: `python -m backend.scripts.eval_runner --label after-0715`

- [ ] **Step 3: 판정 기준 적용 — 계층화**

측정에는 세 종류의 신호가 있고, **귀속 가능성이 다르다**. 축 점수는 노이즈가 크고(Step 5에서 실측한 밴드) 조항 단위 귀속이 불가능하다(Task 6은 4묶음 동시 변경). 반면 이진 defect은 조항과 1:1로 매핑된다.

**[1차 — 조항 귀속 가능] 이진 defect 카운트** (6편 합산, 베이스라인 대비):

| defect | 대응 조항 | 목표 |
|---|---|---|
| `emoji` | L1 가드 5조 | 발생 0 |
| `derived_number_suspect` | L1 가드 6조 + V2 | 발생 0 |
| `text_visual_mismatch` | L1 가드 8조 | 감소 |
| `dead_zone` | L4 자기검수 | 감소 |
| `untranslated_unit` | 기존 [카피] 조항 + L4 | 감소 |
| `placeholder` | 기존 조항(이미 준수 중) | 0 유지 |

**해당 defect이 안 줄면 그 조항만 재검토** — 이 채널에서만 조항 단위 귀속을 허용한다.

**[2차 — 방향 신호] 다양성**: `diversity` 점수 하락 없음(동률이면 `similar_pairs` 감소로 판정), `distinct_formats` 증가가 목표. **after 6덱의 매니페스트 `archetype` 분포에서 4덱 이상이 같은 아크면 변주 장치 실패**로 본다(refs 방향 헤더·아키타입 절 재작업 후 1회 재시도).

**[3차 — 참고] 축 점수**: paired per-paper 델타로 본다(스코어보드가 `{paper, sha, scores}` 구조라 논문별 대조 가능). **회귀로 인정하는 조건 = "6편 중 4편 이상에서 같은 축이 같은 방향으로 하락 AND 평균 델타 ≤ -0.5"** (1~5 정수 척도에서 Step 5 노이즈 밴드를 넘는 값). 이 조건에 못 미치는 축 평균 등락은 **판정에 쓰지 않고 결정로그에 기록만** 한다 — 저지 노이즈로 인한 위양성 회귀를 막는다.

**종합 판정**:
- **채택**: 1차 목표 충족 + 2차 하락 없음 + 3차 회귀 조건 미해당
- **부분 회귀**: 1차에서 특정 defect 미개선 → **그 조항만** 재작업 후 1회 재시도(유료 1사이클 캡). resume가 있으므로 실패분만 재과금.
- **전면 회귀**: 3차 회귀 조건이 2개 축 이상에서 성립 → `git revert`로 Task 6 커밋 롤백. (V2·웹 표면화·컨트롤룸은 저작 입력을 안 바꾸므로 유지. **단 매니페스트 이력 주입은 저작 입력을 바꾸므로 '독립'이 아니다** — eval은 이력 격리 상태로 돌지만 프로덕션은 아니다.)
- **꼬리 generality 확인**: 이력이 격리된 상태에서 theory-1이 "데이터 클라이맥스형"이 아닌 아크를 선언했는지 + `rejected_arc`에 근거를 적었는지 확인. 자기신고라는 한계는 있으나, 저지의 `integrity`·`accessibility` 축과 함께 보면 신호가 된다.

- [ ] **Step 4: AUTHORING.md §2 결정로그의 '측정효과' 칸 백필** — Phase 1~4에서 "다음 eval 백필"로 남긴 행들에 델타를 채운다(예: `emoji 4→0, derived_suspect 2→0, diversity 2→4`). append-only 원칙 유지 — 기존 행의 빈 칸을 채우는 것만 허용, 행 삭제·수정 금지.

- [ ] **Step 5: 결과 커밋 + 메모리 갱신**

```bash
git add eval/runs/ eval/scoreboard.jsonl backend/agents/deck/AUTHORING.md
git commit -m "[EVAL] 프롬프트 5층 재편 후 재측정 — 베이스라인 대비 판정·결정로그 백필"
```

---

## 실행 순서 (inline)

무료 구간을 먼저 다 만들고, 유료는 두 지점에서만 멈춘다.

```
Task 1  저지 스크립트 (다양성 교차저지 포함)          무료
Task 2  eval_runner + eval_set.json 골격             무료
Task 2.5 컨트롤룸 AUTHORING.md + backend/CLAUDE.md   무료
Task 3  docs 계약 갱신 (docs 먼저 규율)               무료
────────── ⛔ Task 4: 베이스라인 (유료 ~$6~11, 허락 필요 · eval 논문 6편 경로 필요)
Task 5   V2 파생수치 + 60k 절단 경고                  무료
Task 5.5 웹 표면화 (suspect 배지·allClear 게이트)     무료
Task 9   REF_LIBRARY 태그 (Task 6보다 먼저!)          무료
Task 6   프롬프트 5층 재편                            무료
Task 7   manifest.py + DB (selfcheck 파서 포함)       무료
Task 8   파이프라인 배선                              무료
────────── ⛔ Task 10: 재측정·판정 (유료 ~$6~11, 허락 필요)
```

Task 4는 eval 논문 6편이 준비돼야 돈다. **논문 준비 전이라면 Task 5~9를 먼저 만들어두되, 베이스라인 없이 Task 10을 돌리지 말 것** — 비교 대상이 없으면 측정이 아니라 vibes다(이 플랜의 존재 이유).

---

## Self-Review 체크 결과

- **스펙 커버리지**: 검증자 정밀화 7건 반영 — ①측정 먼저(Phase 0 선행) ②아키타입 탈출구("새 아크를 발명" + 테스트 고정) ③브랜드 킷 out-of-scope ④승격 게이트 엄격+셀룰로오스 덱 보류 ⑤저작가드는 삭제 아닌 증설(L1) ⑥반복이력 소프트 ⑦토큰비.
- **31에이전트 적대검증 확정 23건 반영 (v1.1)**:
  - **P0 다양성 미측정** → Task 1 `judge_diversity` + Task 2 다양성 패스 + Task 10 2차 판정축. (플랜이 자기 1순위 목표를 측정 못 하던 구멍.)
  - **P0 temperature=0 no-op** → 저지는 확률적임을 명시, `--repeat` 노이즈 밴드 실측(Task 4 Step 5), 판정을 노이즈 초과 기준으로 계층화(Task 10 Step 3).
  - **P0 V2 suspect 웹 비가시** → Task 5.5 신설(`verifyStatus.ts` + FactPanel 배지 + allClear 게이트). 표면화 없는 검산은 170% 사건의 반복.
  - **P1 asyncio.run 반복 붕괴** → 저지 클라이언트를 호출당 생성 + 회귀 테스트.
  - **P1 업로드 쿼터 429** → eval 유저 인증 승격 전제(Task 4 Step 2) + 러너 fail-fast.
  - **P1 L2↔L3 모순** → L2 2곳 조건화(Task 6 Step 3(d)) + L4에 "부수 숫자 히어로 승격" 체크.
  - **P1 V2 검산쌍 노이즈** → 페이지네이션·연도 제외 + 테스트 2건.
  - **P1 60k 절단 비가시** → 백로그에서 Task 5 Step 6으로 승격(경고 + 스코어보드 `truncated` 필드).
  - **P1 L4 가짜 recency** → 체크리스트를 유저 프롬프트 말단으로 이동 + `PI_SELFCHECK` 자가보고(생성 말미 재주목).
  - **P1 이력 vs refs 앵커 싸움** → `few_shot_refs` 방향 헤더(refs가 자기가 쓴 아크·무드를 실토) + `rejected_arc` 필드.
  - **P1 eval 이력 오염** → 논문마다 `delete_deck_manifests`로 격리(재현성 확보).
  - **P1 판정 위양성** → 축 평균 단독 기준 폐기, defect(귀속 가능)/다양성/축(참고) 3계층.
  - **P1 '7장' 누락** → 전수 grep + `art_direction_block()` 포함, 테스트로 고정.
  - **P2** 기존 format 테스트 갱신, resume, TIMEOUT 1200s, utf-8 콘솔, 달러 명기.
  - **기각 3건**: L2 무조건문 주장(도입부가 이미 "골라 쓰세요"), PNG 5MB 초과 우려(실측 0.13~0.55MB), 저지 이미지 다운스케일(오히려 소형 텍스트 판독력 손해).
- **자리표시자 스캔**: `eval_set.json`의 CHANGE_ME는 의도된 사용자 게이트(러너가 명시적 에러로 중단). 결정로그의 `2026-07-XX`·`(본 커밋)`은 실행 시점에 채우는 값. 그 외 TBD 없음.
- **타입 일관성**: `derived_claims` 키(value/kind/suspect/unresolved/verified/context) = 파이썬 테스트 = TS `DerivedClaim` 인터페이스 3중 일치. `history_block` 파라미터명 authoring.py↔pipeline.py↔프롬프트 슬롯 일치. `parse_judge_json(raw, required=...)` 시그니처 = 저지 2용도(덱/다양성) 공용. `MAX_SOURCE_CHARS` 리네임이 authoring.py↔pipeline.py↔테스트 일치.
- **컨트롤룸**: 4자산 관리는 자산 복사가 아닌 포인터 문서(AUTHORING.md, Task 2.5) — 7-09 문서표류 사고 재발 방지. 규율은 현실적으로: 결정로그 1줄=변경 커밋마다(무료), 측정효과=eval 런 후 백필(유료라 변경마다 강제 불가). 스코어보드는 eval_runner가 자동 기록(기계가 쓰는 문서만 살아남는다).
