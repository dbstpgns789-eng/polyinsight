# -*- coding: utf-8 -*-
"""eval 배치 — eval_set.json의 논문을 저작→렌더→저지→다양성까지 돌려 결과 기록.

사용 (유료 — 실행 전 사용자 허락 필수):
  python -m backend.scripts.eval_runner --label baseline
  python -m backend.scripts.eval_runner --label baseline --diversity-only   # PNG 재사용, 저작 안 함

전제: uvicorn 서버 가동 중, EVAL_EMAIL/EVAL_PASSWORD 환경변수.

★eval 유저는 email_verified=1이어야 한다 — 미인증은 일일 3편 상한(UPLOAD_UNVERIFIED_LIMIT)이라
  6편 배치가 4편째부터 429로 죽는다. 429는 즉시 중단(반쪽 베이스라인 커밋 방지).
★resume: 같은 label 재실행 시 results.json의 DONE 논문은 스킵(저작 재과금 방지).
★이력 격리: 논문마다 deck_manifest를 비워 '프롬프트 효과'와 '이력 주입 효과'를 분리 측정한다.
  (격리하지 않으면 2번째 논문부터 앞 덱의 매니페스트를 주입받아 실행 순서에 종속되고,
   런을 반복할수록 조건이 달라져 전후 비교가 깨진다.)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import httpx

from backend.scripts.deck_judge import judge_dir, judge_diversity

BASE_URL = "http://localhost:8000"
POLL_INTERVAL = 5
TIMEOUT_PER_PAPER = 1200   # AUTHOR_TIMEOUT_S=600 + S1(장문 pymupdf 느림) + 렌더 여유

_ROOT = Path(__file__).resolve().parents[2]
_EVAL_SET = _ROOT / "eval" / "eval_set.json"
_SCOREBOARD = _ROOT / "eval" / "scoreboard.jsonl"


def _git_sha() -> str:
    """스코어보드 행에 박을 프롬프트 버전 지문."""
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, cwd=_ROOT)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _login(client: httpx.Client) -> int | None:
    """로그인(세션 쿠키) + DB에서 user id 조회(이력 격리용 — /api/auth/me는 id를 안 준다)."""
    email = os.getenv("EVAL_EMAIL", "")
    pw = os.getenv("EVAL_PASSWORD", "")
    if not email or not pw:
        sys.exit("[ERROR] EVAL_EMAIL / EVAL_PASSWORD 환경변수 필요")
    r = client.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw}, timeout=15)
    if r.status_code != 200:
        sys.exit(f"[ERROR] 로그인 실패: {r.status_code} {r.text[:200]}")

    from backend.core import db
    user = asyncio.run(db.get_user_by_email(email.strip().lower()))
    if not user:
        return None
    if not user.get("email_verified"):
        sys.exit(f"[ERROR] eval 유저 미인증 — 업로드 일일 3편 상한에 걸린다. 승격 후 재실행:\n"
                 f'  python -c "import asyncio; from backend.core import db; '
                 f"u=asyncio.run(db.get_user_by_email('{email}')); "
                 f'asyncio.run(db.set_email_verified(u[\'id\']))"')
    return int(user["id"])


def _clear_history(user_id: int | None) -> None:
    """이력 격리 — deck_manifest 비움. 테이블/함수 미구현(베이스라인 시점)이면 조용히 no-op."""
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
                 "유료 런을 반쪽으로 계속 태우지 않도록 즉시 중단.")
    if r.status_code != 202:
        return {"status": "SUBMIT_FAILED", "detail": r.text[:300], "job_id": None}

    job_id = r.json()["jobId"]
    deadline = time.time() + TIMEOUT_PER_PAPER
    while time.time() < deadline:
        try:
            data = client.get(f"{BASE_URL}/api/status/{job_id}", timeout=15).json()
        except Exception:
            time.sleep(POLL_INTERVAL)
            continue
        print(f"    [{data.get('stage')}] {data.get('progress', 0)}% …", end="\r", flush=True)
        if data.get("status") in ("DONE", "FAILED", "ERROR"):
            print()
            return {"status": data["status"], "job_id": job_id,
                    "warnings": data.get("warnings", ""), "degraded": data.get("degraded", False)}
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


def _run_diversity(run_dir: Path, results: list[dict], label: str, sha: str) -> None:
    """DONE 덱들의 표지를 한 콜에 비교 — 동질화(사용자 1순위 고통)는 크로스덱 속성이다.

    아카이브된 PNG만 쓰므로 베이스라인에도 소급 적용된다(--diversity-only)."""
    covers: list[bytes] = []
    labels: list[str] = []
    for e in sorted([e for e in results if e.get("status") == "DONE"], key=lambda x: x["id"]):
        pngs = sorted((run_dir / e["id"]).glob("*.png"))
        if pngs:
            covers.append(pngs[0].read_bytes())
            labels.append(e["id"])
    if len(covers) < 2:
        print("(다양성 저지 스킵 — 덱 2개 미만)")
        return
    div = asyncio.run(judge_diversity(covers, labels))
    (run_dir / "diversity.json").write_text(
        json.dumps(div, ensure_ascii=False, indent=2), encoding="utf-8")
    if not div:
        print("(다양성 저지 응답 파싱 실패)")
        return
    print(f"다양성: {div.get('diversity')}/5 · 구별 포맷 {div.get('distinct_formats')}종 "
          f"· 닮은 쌍 {div.get('similar_pairs')}")
    with _SCOREBOARD.open("a", encoding="utf-8") as sb:
        sb.write(json.dumps({
            "label": label, "sha": sha, "paper": "_diversity",
            "diversity": div.get("diversity"),
            "distinct_formats": div.get("distinct_formats"),
            "similar_pairs": div.get("similar_pairs"),
        }, ensure_ascii=False) + "\n")


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")   # Windows cp949 콘솔 방어
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="eval 배치 (유료)")
    ap.add_argument("--label", required=True, help="런 라벨 (baseline, after-0715 등)")
    ap.add_argument("--diversity-only", action="store_true",
                    help="저작 없이 아카이브된 PNG로 다양성 저지만 재실행")
    args = ap.parse_args()

    spec = json.loads(_EVAL_SET.read_text(encoding="utf-8"))
    papers = spec["papers"]
    run_dir = _ROOT / "eval" / "runs" / args.label
    run_dir.mkdir(parents=True, exist_ok=True)
    results_path = run_dir / "results.json"
    sha = _git_sha()

    if args.diversity_only:
        if not results_path.exists():
            sys.exit(f"[ERROR] {results_path} 없음 — 먼저 본 런을 돌려라")
        results = json.loads(results_path.read_text(encoding="utf-8"))
        _run_diversity(run_dir, results, args.label, sha)
        return

    missing = [p["id"] for p in papers if p["path"] == "CHANGE_ME.pdf" or not Path(p["path"]).exists()]
    if missing:
        sys.exit(f"[ERROR] eval_set.json 경로 미지정/없음: {missing}")

    results: list[dict] = []
    done_ids: set[str] = set()
    if results_path.exists():   # resume — 실패분만 재실행, DONE 저작비 재과금 방지
        results = json.loads(results_path.read_text(encoding="utf-8"))
        done_ids = {e["id"] for e in results if e.get("status") == "DONE"}
        print(f"[resume] 기존 결과 {len(results)}건 로드 — DONE {len(done_ids)}편 스킵")

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

            badge = {"DONE": "OK", "TIMEOUT": "TIMEOUT"}.get(entry["status"], "FAIL")
            print(f"  [{badge}] {entry['status']}"
                  + (f" · 저지 {entry['judge']['verdict']}" if entry.get("judge") else ""))

            # 스코어보드는 기계가 쓴다 — 사람 손 안 탐(살아있는 문서의 조건)
            if entry.get("judge"):
                with _SCOREBOARD.open("a", encoding="utf-8") as sb:
                    sb.write(json.dumps({
                        "label": args.label, "sha": sha, "paper": p["id"], "genre": p["genre"],
                        "scores": entry["judge"]["scores"], "verdict": entry["judge"]["verdict"],
                        "defects": entry["judge"]["defects"],
                        "truncated": "SOURCE_TRUNCATED" in str(entry.get("warnings", "")),
                    }, ensure_ascii=False) + "\n")

    _run_diversity(run_dir, results, args.label, sha)

    ok = [e for e in results if e.get("judge")]
    if ok:
        print("\n=== 축별 평균 ===")
        for a in ("hook", "narrative", "accessibility", "integrity", "finish"):
            avg = sum(e["judge"]["scores"][a] for e in ok) / len(ok)
            print(f"  {a:14}: {avg:.2f}")
    failed = [e["id"] for e in results if e.get("status") != "DONE"]
    if failed:
        print(f"\n⚠ 미완료 {failed} — 베이스라인/재측정 커밋 금지. 원인 해결 후 같은 label로 재실행(resume).")
    print(f"결과: {results_path}")


if __name__ == "__main__":
    main()
