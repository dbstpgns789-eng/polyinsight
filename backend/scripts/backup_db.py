"""SQLite 백업 — VACUUM INTO 스냅샷 + 최근 N개 보존.

사용법: python -m backend.scripts.backup_db [--keep 7] [--dest backups]
(루트에서 실행 — DATABASE_URL이 상대경로라 cwd가 루트여야 함)

복원 리허설 6단계:
  1. uvicorn 정지
  2. 기존 ./polyinsight.db → polyinsight.db.broken 으로 rename
  3. backups/polyinsight_YYYYMMDD_HHMMSS.db 를 ./polyinsight.db 로 복사
  4. 잔존 polyinsight.db-wal / polyinsight.db-shm 삭제
  5. uvicorn 기동
  6. 로그인 확인

Windows 스케줄 등록(일 1회 03:00):
  schtasks /Create /TN PolyInsightBackup /SC DAILY /ST 03:00 /TR "cmd /c cd /d <레포루트> && .venv\\Scripts\\python.exe -m backend.scripts.backup_db"

배포 후 리눅스 크론:
  0 3 * * * cd /path/to/polyinsight && .venv/bin/python -m backend.scripts.backup_db
"""
from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime

_PATTERN = re.compile(r"polyinsight_\d{8}_\d{6}\.db")


def _count(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def _ro_connect(path: str) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def backup(db_path: str, dest: str, keep: int = 7, min_bytes: int = 1_000_000) -> str:
    """스냅샷 생성→사후검증→보존정리. 성공 시 백업 경로 반환, 실패 시 RuntimeError."""
    db_path = os.path.abspath(db_path)
    size = os.path.getsize(db_path)
    print(f"원본: {db_path} ({size:,} bytes)")
    if size < min_bytes:
        raise RuntimeError(f"원본이 {min_bytes:,} bytes 미만 — 엉뚱한 DB 방지 abort (cwd 확인)")

    os.makedirs(dest, exist_ok=True)
    final = os.path.join(dest, f"polyinsight_{datetime.now():%Y%m%d_%H%M%S}.db")
    tmp = final + ".tmp"
    if os.path.exists(tmp):
        os.remove(tmp)  # VACUUM INTO는 선존재 파일에 실패
    with sqlite3.connect(db_path) as src:
        src.execute("VACUUM INTO ?", (tmp,))
    os.replace(tmp, final)

    # 사후검증 — 백업본 ro로 열어 integrity + 행 수 원본 대조
    with _ro_connect(db_path) as src, _ro_connect(final) as bak:
        ok = bak.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {t: (_count(src, t), _count(bak, t)) for t in ("users", "jobs")}
    print(f"백업: {final} ({os.path.getsize(final):,} bytes) integrity={ok} counts={counts}")
    if ok != "ok" or any(s != b for s, b in counts.values()):
        raise RuntimeError("사후검증 실패 — 백업본은 삭제하지 않음. 수동 확인 필요")

    # 보존 — 타임스탬프 정확 패턴만 대상. 수동 네이밍 백업은 건드리지 않음.
    snaps = sorted(f for f in os.listdir(dest) if _PATTERN.fullmatch(f))
    for old in snaps[:-keep] if keep > 0 else []:
        os.remove(os.path.join(dest, old))
        print(f"보존정리 삭제: {old}")
    return final


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite VACUUM INTO 백업")
    parser.add_argument("--keep", type=int, default=7, help="보존 개수 (기본 7)")
    parser.add_argument("--dest", default="backups", help="백업 폴더 (기본 backups/)")
    args = parser.parse_args()

    from backend.core.db import _db_path

    try:
        backup(_db_path(), args.dest, keep=args.keep)
    except RuntimeError as e:
        print(f"실패: {e}")
        sys.exit(1)
