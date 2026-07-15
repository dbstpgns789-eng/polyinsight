"""golden22 배치 제출 — 웹 업로드와 동일한 API 경로.

사용:
  python -m backend.scripts.golden_batch --corpus <golden_22_경로>

동작:
  1. X-Render-Token으로 인증 우회 (서비스 계정)
  2. 각 PDF → POST /api/upload (multipart)
  3. GET /api/status/{jobId} 폴링 → DONE/FAILED 대기
  4. 콘솔 + 로그 파일에 전체 결과 기록
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

BASE_URL = "http://localhost:8000"
RENDER_TOKEN = os.getenv("RENDER_TOKEN", "")
POLL_INTERVAL = 5   # seconds
TIMEOUT_PER_PAPER = 600  # 10분 타임아웃

_HEADERS = {"x-render-token": RENDER_TOKEN}


# ── 서버 연결 확인 ────────────────────────────────────────────────────────────

def _check_server(client: httpx.Client) -> bool:
    try:
        # /api/health 없음 — docs 엔드포인트로 연결 확인
        r = client.get(f"{BASE_URL}/docs", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# ── 단일 논문 제출 + 폴링 ──────────────────────────────────────────────────────

def submit_and_wait(client: httpx.Client, pdf_path: Path, card_count: int = 7) -> dict:
    """PDF 제출 → 완료까지 폴링 → 결과 dict 반환."""
    # 1. 업로드
    with pdf_path.open("rb") as f:
        r = client.post(
            f"{BASE_URL}/api/upload",
            files={"file": (pdf_path.name, f, "application/pdf")},
            data={"card_count": str(card_count)},
            headers=_HEADERS,
            timeout=30,
        )
    if r.status_code != 202:
        return {
            "file": pdf_path.name,
            "status": "SUBMIT_FAILED",
            "detail": r.text,
            "job_id": None,
        }

    job_id = r.json()["jobId"]

    # 2. 폴링
    deadline = time.time() + TIMEOUT_PER_PAPER
    while time.time() < deadline:
        try:
            sr = client.get(f"{BASE_URL}/api/status/{job_id}", headers=_HEADERS, timeout=10)
            data = sr.json()
        except Exception as exc:
            time.sleep(POLL_INTERVAL)
            continue

        status = data.get("status", "")
        stage = data.get("stage", "")
        progress = data.get("progress", 0)
        print(f"    [{stage}] {progress}% …", end="\r", flush=True)

        if status in ("DONE", "FAILED", "ERROR"):
            print()  # newline after \r
            return {
                "file": pdf_path.name,
                "job_id": job_id,
                "status": status,
                "stage": stage,
                "degraded": data.get("degraded", False),
                "warnings": data.get("warnings", ""),
            }
        time.sleep(POLL_INTERVAL)

    return {
        "file": pdf_path.name,
        "job_id": job_id,
        "status": "TIMEOUT",
        "stage": "unknown",
        "degraded": False,
        "warnings": f"폴링 타임아웃 {TIMEOUT_PER_PAPER}초",
    }


# ── 메인 ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser(description="golden22 배치 제출")
    ap.add_argument("--corpus", required=True, help="golden_22 폴더 경로")
    ap.add_argument("--card-count", type=int, default=7, help="카드 수 (3~7, 기본 7)")
    ap.add_argument("--log", default="golden_batch_result.json", help="결과 저장 경로")
    ap.add_argument("--dry-run", action="store_true", help="파일 목록만 출력, 실제 제출 안 함")
    args = ap.parse_args()

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # RENDER_TOKEN 환경변수 로드 (dotenv 없으면 .env 직접 파싱)
    global RENDER_TOKEN, _HEADERS
    if not RENDER_TOKEN:
        env_path = Path(__file__).parents[2] / "backend" / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("RENDER_TOKEN="):
                    RENDER_TOKEN = line.split("=", 1)[1].strip()
                    _HEADERS = {"x-render-token": RENDER_TOKEN}
                    break
    if not RENDER_TOKEN:
        print("[ERROR] RENDER_TOKEN 없음. backend/.env 확인 필요.", file=sys.stderr)
        sys.exit(1)

    pdfs = sorted(Path(args.corpus).glob("*.pdf"))
    if not pdfs:
        print(f"[ERROR] PDF 없음: {args.corpus}", file=sys.stderr)
        sys.exit(1)

    print(f"[golden_batch] {len(pdfs)}편 발견 · 카드={args.card_count}장 · 서버={BASE_URL}")

    if args.dry_run:
        for i, p in enumerate(pdfs, 1):
            print(f"  [{i:02}/{len(pdfs)}] {p.name}")
        return

    with httpx.Client() as client:
        if not _check_server(client):
            print(f"[ERROR] 서버 응답 없음: {BASE_URL}  →  uvicorn 실행 확인", file=sys.stderr)
            sys.exit(1)

        results: list[dict] = []
        done = fail = timeout = 0

        for i, pdf in enumerate(pdfs, 1):
            print(f"[{i:02}/{len(pdfs)}] {pdf.name}")
            result = submit_and_wait(client, pdf, args.card_count)
            results.append(result)

            st = result["status"]
            badge = {"DONE": "✅", "FAILED": "❌", "ERROR": "❌", "TIMEOUT": "⏱", "SUBMIT_FAILED": "🚫"}.get(st, "?")
            degraded_tag = " (degraded)" if result.get("degraded") else ""
            print(f"  {badge} {st}{degraded_tag}  job={result.get('job_id', '-')}")
            if result.get("warnings"):
                print(f"     warnings: {result['warnings'][:120]}")

            if st == "DONE": done += 1
            elif st == "TIMEOUT": timeout += 1
            else: fail += 1

    # 결과 저장
    log_path = Path(args.log)
    log_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*50}")
    print(f"=== golden_batch 완료 ===")
    print(f"  DONE    : {done}/{len(pdfs)}")
    print(f"  FAILED  : {fail}/{len(pdfs)}")
    print(f"  TIMEOUT : {timeout}/{len(pdfs)}")
    print(f"  로그    : {log_path.resolve()}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
