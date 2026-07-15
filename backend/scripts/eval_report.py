# -*- coding: utf-8 -*-
"""eval 판정 리포트 — 스코어보드/런 결과를 계층화 기준으로 읽는다 (무료, LLM 호출 없음).

사용:
  python -m backend.scripts.eval_report --label after-0712 [--baseline-judge <path>]

판정 계층 (플랜 Task 10 Step 3):
  1차 이진 defect — 조항과 1:1 매핑되어 **귀속 가능**. 이게 판정의 정본.
  2차 다양성      — 덱 간 동질화(사용자 1순위 고통). 크로스덱 속성.
  3차 축 점수     — 저지가 확률적(sonnet-5는 sampling 파라미터를 안 받음)이라 노이즈가 크다.
                    참고용이며, 노이즈 밴드를 넘는 변화만 신호로 읽는다.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]

_AXES = ("hook", "narrative", "accessibility", "integrity", "finish")

# defect → 이를 막으라고 넣은 조항 (귀속 가능한 유일한 채널)
_DEFECT_CLAUSE = {
    "emoji": "L1 가드 5조 (이모지 금지)",
    "derived_number_suspect": "L1 가드 6조 (파생수치 재검산) + V2",
    "text_visual_mismatch": "L1 가드 8조 (그림=본문 형상)",
    "dead_zone": "L4 자기검수 (세로 3분할 빈 구획)",
    "untranslated_unit": "[카피] 단위 번역 + L4",
    "placeholder": "기존 조항 (자리표시자 금지)",
}


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="eval 판정 리포트")
    ap.add_argument("--label", required=True)
    ap.add_argument("--baseline-judge", default="eval/runs/baseline-oldprompt/microbead-cof-judge.json",
                    help="구 프롬프트 덱의 저지 결과(같은 논문 1편 전후 비교용)")
    ap.add_argument("--baseline-paper", default="microbead-cof")
    args = ap.parse_args()

    run_dir = _ROOT / "eval" / "runs" / args.label
    results = json.loads((run_dir / "results.json").read_text(encoding="utf-8"))
    done = [e for e in results if e.get("status") == "DONE" and e.get("judge")]
    print(f"=== {args.label} · {len(done)}/{len(results)}편 저작·심사 완료 ===\n")

    # 저작 지문은 DB의 덱 HTML에서 직접 읽는다(러너 결과에 없어도 사후 판독 가능)
    from backend.agents.deck.manifest import parse_manifest, selfcheck_failures
    from backend.core import db

    async def _load_manifests() -> None:
        for e in done:
            deck = await db.get_authored_deck(e["job_id"])
            html = (deck or {}).get("html") or ""
            e["manifest"] = parse_manifest(html) or {}
            e["selfcheck_fails"] = selfcheck_failures(html)

    asyncio.run(_load_manifests())

    # ── 1차: 이진 defect (조항 귀속) ──────────────────────────────────────
    print("[1차] 결함 발생 — 조항 귀속 가능한 정본 채널")
    counts: dict[str, int] = {}
    for e in done:
        for k, v in (e["judge"].get("defects") or {}).items():
            counts[k] = counts.get(k, 0) + (1 if v else 0)
    for k in _DEFECT_CLAUSE:
        n = counts.get(k, 0)
        mark = "OK  " if n == 0 else "MISS"
        who = [e["id"] for e in done if (e["judge"].get("defects") or {}).get(k)]
        print(f"  [{mark}] {k:24} {n}/{len(done)}편"
              + (f"  ← {_DEFECT_CLAUSE[k]}  {who}" if n else ""))

    # ── 2차: 다양성 ──────────────────────────────────────────────────────
    div_path = run_dir / "diversity.json"
    print("\n[2차] 덱 간 다양성 — 동질화(사용자 1순위 고통)")
    if div_path.exists():
        d = json.loads(div_path.read_text(encoding="utf-8")) or {}
        print(f"  diversity {d.get('diversity')}/5 · 구별 포맷 {d.get('distinct_formats')}종")
        print(f"  닮은 쌍: {d.get('similar_pairs')}")
        print(f"  \"{d.get('one_line')}\"")
    else:
        print("  (diversity.json 없음)")

    # 매니페스트 아크·팔레트 분포 — 과반이 같은 아크면 변주 장치 실패
    print("\n  선언된 아크 분포(PI_MANIFEST 자기신고):")
    arcs: dict[str, list[str]] = {}
    for e in done:
        m = e.get("manifest") or {}
        arcs.setdefault(m.get("archetype", "(미선언)"), []).append(e["id"])
    for arc, ids in sorted(arcs.items(), key=lambda x: -len(x[1])):
        print(f"    {arc:22} {len(ids)}편  {ids}")
    print("\n  선언된 팔레트·모티프:")
    for e in done:
        m = e.get("manifest") or {}
        print(f"    {e['id']:24} {str(m.get('palette', '?'))[:34]:36} / {str(m.get('motif', '?'))[:20]}")
    rej = [e for e in done if (e.get("manifest") or {}).get("rejected_arc")]
    print(f"\n  rejected_arc 근거 기입: {len(rej)}/{len(done)}편 (1번 아크 디폴트 픽 방지 장치)")

    # ── 3차: 축 점수 (참고 — 노이즈 큼) ──────────────────────────────────
    print("\n[3차] 축 점수 (참고 — 저지는 확률적, 노이즈 밴드 밖만 신호)")
    for a in _AXES:
        vals = [e["judge"]["scores"][a] for e in done]
        avg = sum(vals) / len(vals) if vals else 0
        print(f"  {a:14} {avg:.2f}   {vals}")
    verdicts: dict[str, int] = {}
    for e in done:
        v = e["judge"].get("verdict", "?")
        verdicts[v] = verdicts.get(v, 0) + 1
    print(f"  verdict 분포: {verdicts}")

    # ── 전후 비교 (같은 논문 1편) ────────────────────────────────────────
    bj = _ROOT / args.baseline_judge
    after = next((e for e in done if e["id"] == args.baseline_paper), None)
    if bj.exists() and after:
        base = json.loads(bj.read_text(encoding="utf-8"))
        print(f"\n[전후] {args.baseline_paper} — 구 프롬프트 vs 신 프롬프트 (유일한 paired 비교)")
        print(f"  {'축':14} {'구':>4} {'신':>4}")
        for a in _AXES:
            b, n = base["scores"][a], after["judge"]["scores"][a]
            arrow = "→" if b == n else ("↑" if n > b else "↓")
            print(f"  {a:14} {b:>4} {n:>4}  {arrow}")
        print(f"  {'verdict':14} {base['verdict']:>4} {after['judge']['verdict']:>4}")
        print("  결함:")
        for k in _DEFECT_CLAUSE:
            b = bool(base["defects"].get(k))
            n = bool((after["judge"].get("defects") or {}).get(k))
            if b or n:
                fixed = "FIXED" if b and not n else ("NEW" if n and not b else "그대로")
                print(f"    {k:24} 구={'O' if b else 'X'} 신={'O' if n else 'X'}  [{fixed}]")

    # ── V2 검산 결과 ─────────────────────────────────────────────────────
    print("\n[V2] 파생수치 산수 검산 (코드 — 저지와 독립)")
    for e in done:
        der = ((e.get("verify") or {}).get("derived")) or []
        sus = [d for d in der if d.get("suspect")]
        unv = (e.get("verify") or {}).get("unverified", "?")
        print(f"  {e['id']:24} 파생 {len(der)}건 · suspect {len(sus)}건 · 원문미확인 {unv}건"
              + (f"  {[d['value'] for d in sus]}" if sus else ""))

    # ── 자가검수 신고 (PI_SELFCHECK) ─────────────────────────────────────
    print("\n[L4] 모델 자가검수 신고 — 저지 판정과 대조하면 자기검수의 실효를 안다")
    for e in done:
        fails = e.get("selfcheck_fails")
        real = [k for k, v in (e["judge"].get("defects") or {}).items() if v]
        print(f"  {e['id']:24} 자가신고 실패={fails or '없음(전항 통과)'} / 저지 판정 결함={real or '없음'}")

    # ── 경고(절단·매니페스트·자가검수) ───────────────────────────────────
    print("\n[경고] 파이프라인 표면화")
    for e in results:
        w = e.get("warnings") or ""
        if w and w not in ("[]", "null"):
            print(f"  {e['id']:24} {str(w)[:150]}")


if __name__ == "__main__":
    main()
