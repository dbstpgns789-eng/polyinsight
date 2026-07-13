# -*- coding: utf-8 -*-
"""백엔드 서버를 **설정 적용까지 검증하며** 재시작한다.

왜 필요한가(이번 세션에 두 번 당함): `pkill` 후 새 서버를 띄우는데 기존 프로세스가 안 죽으면
새 서버는 바인드 실패로 조용히 죽고, **curl은 200을 반환한다**(기존 서버가 응답하니까).
그래서 설정이 안 바뀐 줄 모르고 유료 실험을 태운다 — 실제로 Best-of-3 실험이 candidates=1로
돌았다. **200 OK는 '내 설정이 적용됐다'는 뜻이 아니다.**

사용:
  python -m backend.scripts.restart_server --env AUTHOR_CANDIDATES=3 --env AUTHOR_VISION_ROUNDS=2
  python -m backend.scripts.restart_server            # 기본값으로

포트 점유가 안 풀리면 **실패로 종료**한다 — 조용히 옛 서버를 쓰느니 멈추는 게 낫다.
"""
from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx

_ROOT = Path(__file__).resolve().parents[2]
PORT = 8000
BASE = f"http://localhost:{PORT}"


def _port_busy() -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", PORT)) == 0


def _kill_all() -> None:
    """uvicorn 프로세스 전부 종료(Windows/POSIX 공용)."""
    if os.name == "nt":
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -like '*uvicorn*' } | "
             "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"],
            capture_output=True,
        )
    else:
        subprocess.run(["pkill", "-f", "uvicorn backend.main"], capture_output=True)


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="설정 적용을 검증하며 서버 재시작")
    ap.add_argument("--env", action="append", default=[], help="KEY=VALUE (반복 가능)")
    ap.add_argument("--log", default="/tmp/uvicorn.log")
    args = ap.parse_args()

    overrides = {}
    for kv in args.env:
        k, _, v = kv.partition("=")
        overrides[k.strip()] = v.strip()

    # 1) 기존 서버 종료 — 포트가 풀릴 때까지 확인
    _kill_all()
    for _ in range(20):
        if not _port_busy():
            break
        time.sleep(0.5)
    else:
        sys.exit(f"[FAIL] 포트 {PORT}가 여전히 점유 중입니다. 남은 프로세스를 직접 종료하세요.\n"
                 "       (조용히 옛 서버를 쓰면 유료 실험이 잘못된 설정으로 돕니다.)")

    # 2) 새 서버 기동
    env = {**os.environ, "PYTHONUTF8": "1", **overrides}
    logf = open(args.log, "w", encoding="utf-8")
    subprocess.Popen(
        [str(_ROOT / ".venv/Scripts/python.exe"), "-m", "uvicorn",
         "backend.main:app", "--host", "0.0.0.0", "--port", str(PORT)],
        cwd=str(_ROOT), env=env, stdout=logf, stderr=subprocess.STDOUT,
    )

    # 3) 살아났는지 확인
    for _ in range(40):
        try:
            if httpx.get(f"{BASE}/docs", timeout=2).status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.5)
    else:
        sys.exit(f"[FAIL] 서버가 뜨지 않았습니다. 로그: {args.log}")

    # 4) ★설정이 실제로 적용됐는지 검증 — 200 OK는 '내 설정이 반영됐다'는 뜻이 아니다
    log_text = Path(args.log).read_text(encoding="utf-8", errors="ignore")
    if "10048" in log_text or "already in use" in log_text.lower():
        sys.exit("[FAIL] 새 서버가 바인드에 실패했습니다(기존 서버가 응답 중). "
                 "설정이 적용되지 않았습니다 — 유료 실험을 돌리지 마세요.")

    print(f"[OK] 서버 기동 · 로그 {args.log}")
    if overrides:
        print("     적용 요청:", ", ".join(f"{k}={v}" for k, v in overrides.items()))
        print("     ※ 실제 적용 여부는 첫 저작의 llm_calls·input_tokens로 교차확인하세요.")


if __name__ == "__main__":
    main()
