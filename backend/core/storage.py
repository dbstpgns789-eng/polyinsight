"""파일 저장 단일 창구 (L1 — Storage 경계).

async 시그니처 = R2 등 네트워크 백엔드가 나중에 같은 계약으로 끼워지게 하는 이유(L5).
get_storage()는 무상태 — 매 호출 settings.STORAGE_DIR 라이브 read (db._db_path 패턴).
이 무캐시 속성이 테스트 격리(monkeypatch로 tmp 주입)를 성립시킨다.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import Protocol

from .config import settings


class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...
    async def get(self, key: str) -> bytes | None: ...
    async def delete(self, key: str) -> None: ...
    async def delete_prefix(self, prefix: str) -> None: ...


class FilesystemStorage:
    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        # 키는 앱이 uuid로 생성하지만 '..' 탈출 방어.
        dest = (self._root / key).resolve()
        if dest != self._root and self._root not in dest.parents:
            raise ValueError(f"unsafe storage key: {key!r}")
        return dest

    def _put_sync(self, key: str, data: bytes) -> None:
        dest = self._path(key)
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_name(f"{dest.name}.{uuid.uuid4().hex}.tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        # 같은 파일시스템 내 rename = 원자적(각자 완전한 temp를 스왑 → torn 파일 불가).
        # Windows: 동일 dest에 동시 os.replace가 몰리면 일시적 PermissionError(WinError 5) →
        # 원자성은 유지되므로 짧게 재시도로 경합만 흡수(POSIX엔 사실상 미발생).
        for attempt in range(40):
            try:
                os.replace(tmp, dest)
                return
            except PermissionError:
                if attempt == 39:
                    try:
                        os.remove(tmp)
                    except FileNotFoundError:
                        pass
                    raise
                time.sleep(0.005)

    def _get_sync(self, key: str) -> bytes | None:
        try:
            with open(self._path(key), "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def _delete_sync(self, key: str) -> None:
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass

    def _delete_prefix_sync(self, prefix: str) -> None:
        shutil.rmtree(self._path(prefix), ignore_errors=True)

    async def put(self, key: str, data: bytes) -> None:
        await asyncio.to_thread(self._put_sync, key, data)

    async def get(self, key: str) -> bytes | None:
        return await asyncio.to_thread(self._get_sync, key)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._delete_sync, key)

    async def delete_prefix(self, prefix: str) -> None:
        await asyncio.to_thread(self._delete_prefix_sync, prefix)


def get_storage() -> FilesystemStorage:
    return FilesystemStorage(settings.STORAGE_DIR)
