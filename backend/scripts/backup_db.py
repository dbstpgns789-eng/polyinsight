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
  7. (L1) backups/assets_*.tar.gz 를 STORAGE_DIR에 풀기:
     tar xzf assets_YYYYMMDD_HHMMSS.tar.gz -C <STORAGE_DIR>
     ⚠️ DB 스냅샷과 같은 시점 쌍으로 복원 — storage_key(DB)와 파일이 어긋나면 dangling.

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
        # 기준 행 수를 VACUUM 직전에 읽음 — 검증 시점에 다시 읽으면
        # 라이브 쓰기가 끼어들어 정상 스냅샷을 실패로 오판(TOCTOU)
        pre = {t: _count(src, t) for t in ("users", "jobs")}
        src.execute("VACUUM INTO ?", (tmp,))
    os.replace(tmp, final)

    # 사후검증 — 백업본 ro로 열어 integrity + 스냅샷 직전 행 수와 대조
    with _ro_connect(final) as bak:
        ok = bak.execute("PRAGMA integrity_check").fetchone()[0]
        counts = {t: (pre[t], _count(bak, t)) for t in ("users", "jobs")}
    print(f"백업: {final} ({os.path.getsize(final):,} bytes) integrity={ok} counts={counts}")
    if ok != "ok" or any(s != b for s, b in counts.values()):
        # 실패본을 타임스탬프 이름 그대로 두면 보존정리 슬롯을 차지해
        # 검증된 옛 백업을 밀어냄 — 패턴 밖으로 rename해 증거만 보존
        os.replace(final, final + ".unverified")
        raise RuntimeError(f"사후검증 실패 — {final}.unverified 로 보존. 수동 확인 필요")

    # 보존 — 타임스탬프 정확 패턴만 대상. 수동 네이밍 백업은 건드리지 않음.
    snaps = sorted(f for f in os.listdir(dest) if _PATTERN.fullmatch(f))
    for old in snaps[:-keep] if keep > 0 else []:
        os.remove(os.path.join(dest, old))
        print(f"보존정리 삭제: {old}")
    return final


def backup_assets(storage_dir: str, dest: str) -> str | None:
    """영속 자산(jobs/*/assets/)만 tar.gz 스냅샷 (L1 — 바이너리가 DB 밖으로 나가 생긴 백업 공백 차단).
    TTL 재생성 가능한 cards/·exports/는 제외. 반환=스냅샷 경로 또는 대상 없음 시 None."""
    import tarfile
    src_root = os.path.join(storage_dir, "jobs")
    if not os.path.isdir(src_root):
        print(f"자산 백업 대상 없음: {src_root}")
        return None
    os.makedirs(dest, exist_ok=True)
    out = os.path.join(dest, f"assets_{datetime.now():%Y%m%d_%H%M%S}.tar.gz")
    count = 0
    with tarfile.open(out, "w:gz") as tar:
        for job in os.listdir(src_root):
            adir = os.path.join(src_root, job, "assets")
            if os.path.isdir(adir):
                tar.add(adir, arcname=os.path.join("jobs", job, "assets"))
                count += 1
    print(f"자산 백업: {out} (job {count}개 assets)")
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SQLite VACUUM INTO 백업")
    parser.add_argument("--keep", type=int, default=7, help="보존 개수 (기본 7)")
    parser.add_argument("--dest", default="backups", help="백업 폴더 (기본 backups/)")
    parser.add_argument("--min-bytes", type=int, default=1_000_000,
                        help="원본 최소 크기 가드 (기본 1MB — 신규 소형 DB는 낮춰서 실행)")
    args = parser.parse_args()

    from backend.core.db import _db_path

    try:
        backup(_db_path(), args.dest, keep=args.keep, min_bytes=args.min_bytes)
        from backend.core.config import settings as _settings
        backup_assets(_settings.STORAGE_DIR, args.dest)   # L1 영속 자산 스냅샷
    except RuntimeError as e:
        print(f"실패: {e}")
        sys.exit(1)
