"""파일 저장 단일 창구 (L1 — Storage 경계).

async 시그니처 = R2 등 네트워크 백엔드가 나중에 같은 계약으로 끼워지게 하는 이유(L5).
get_storage()는 무상태 — 매 호출 settings.STORAGE_DIR 라이브 read (db._db_path 패턴).
이 무캐시 속성이 테스트 격리(monkeypatch로 tmp 주입)를 성립시킨다.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import threading
import time
import uuid
from typing import Protocol

from .config import settings

# os.replace를 프로세스 전역으로 직렬화 — Windows에서 같은 dest에 동시 replace가 몰리면
# 일시적 PermissionError(WinError 5). replace는 마이크로초라 직렬화해도 처리량 영향 무시가능.
# (단일 프로세스 운영 전제 — memory project_lab_deployment. 원자성은 temp+replace가 보장.)
_replace_lock = threading.Lock()


class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...
    async def get(self, key: str) -> bytes | None: ...
    async def delete(self, key: str) -> None: ...
    async def delete_prefix(self, prefix: str) -> None: ...


class FilesystemStorage:
    def __init__(self, root: str) -> None:
        # abspath/normpath = 문자열 연산(cwd만 읽고 파일시스템 stat 없음) → 스레드세이프.
        self._root = os.path.normpath(os.path.abspath(root))

    def _path(self, key: str) -> str:
        # '..' 탈출 방어 — normpath는 순수 문자열(resolve()와 달리 FS 미접근 → 동시 쓰기 경합 없음).
        dest = os.path.normpath(os.path.join(self._root, key))
        if dest != self._root and not dest.startswith(self._root + os.sep):
            raise ValueError(f"unsafe storage key: {key!r}")
        return dest

    def _put_sync(self, key: str, data: bytes) -> None:
        dest = self._path(key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        tmp = f"{dest}.{uuid.uuid4().hex}.tmp"
        with open(tmp, "wb") as f:
            f.write(data)
        # 같은 파일시스템 내 rename = 원자적(각자 완전한 temp를 스왑 → torn 파일 불가).
        # 전역 락으로 replace 직렬화(동시 경합 제거) + 소량 재시도(Defender/인덱서가 갓 만든
        # 파일을 스캔하며 거는 잔여 일시 denial 흡수). 정상 경로는 즉시 성공(락 μs).
        with _replace_lock:
            for attempt in range(10):
                try:
                    os.replace(tmp, dest)
                    return
                except PermissionError:
                    if attempt == 9:
                        try:
                            os.remove(tmp)
                        except FileNotFoundError:
                            pass
                        raise
                    time.sleep(0.02)

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
