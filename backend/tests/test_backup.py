"""백업 스크립트 테스트 — VACUUM INTO 스냅샷·라이브 중 백업·보존정책."""
from __future__ import annotations

import os
import sqlite3

import pytest

from backend.scripts.backup_db import backup


@pytest.fixture
def src_db(tmp_path):
    """WAL 모드 소형 DB (users 3행 / jobs 2행)."""
    path = str(tmp_path / "src.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT)")
    conn.execute("CREATE TABLE jobs (job_id TEXT PRIMARY KEY, status TEXT)")
    conn.executemany("INSERT INTO users (email) VALUES (?)",
                     [("a@x.com",), ("b@x.com",), ("c@x.com",)])
    conn.executemany("INSERT INTO jobs VALUES (?, ?)",
                     [("j1", "done"), ("j2", "done")])
    conn.commit()
    conn.close()
    return path


def _counts(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as c:
        return (c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0])


def test_backup_row_counts_match(src_db, tmp_path):
    dest = str(tmp_path / "backups")
    out = backup(src_db, dest, min_bytes=0)
    assert os.path.exists(out)
    assert _counts(out) == (3, 2)


def test_backup_while_write_connection_open(src_db, tmp_path):
    """WAL 라이브 중(쓰기 커넥션 열린 채) 백업 성공."""
    dest = str(tmp_path / "backups")
    writer = sqlite3.connect(src_db)
    writer.execute("INSERT INTO users (email) VALUES ('d@x.com')")
    writer.commit()
    try:
        out = backup(src_db, dest, min_bytes=0)
    finally:
        writer.close()
    assert _counts(out) == (4, 2)


def test_retention_deletes_only_timestamp_pattern(src_db, tmp_path):
    dest = tmp_path / "backups"
    dest.mkdir()
    # 패턴 안(오래된 스냅샷 3개) + 패턴 밖(수동 네이밍 2개)
    old_snaps = ["polyinsight_20200101_000000.db",
                 "polyinsight_20200102_000000.db",
                 "polyinsight_20200103_000000.db"]
    manual = ["polyinsight_20260702_145717_pre_ultracode.db",
              "polyinsight_manual.db"]
    for name in old_snaps + manual:
        (dest / name).write_bytes(b"x")

    backup(src_db, str(dest), keep=1, min_bytes=0)

    remaining = sorted(os.listdir(dest))
    for name in manual:
        assert name in remaining          # 수동 네이밍은 절대 안 지워짐
    for name in old_snaps:
        assert name not in remaining      # keep=1 초과 스냅샷은 삭제
    snaps = [f for f in remaining if f not in manual]
    assert len(snaps) == 1                # 방금 만든 백업만 남음


def test_abort_when_source_too_small(src_db, tmp_path):
    """min_bytes 가드 — 엉뚱한(빈) DB 백업 방지."""
    with pytest.raises(RuntimeError):
        backup(src_db, str(tmp_path / "backups"), min_bytes=10**9)
