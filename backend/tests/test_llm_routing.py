"""LLMClient.call 의 per-call 모델 오버라이드 + 모델 인지 천장 (Task 1)."""
from __future__ import annotations

import pathlib
import sys
import types

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parents[2]))

from unittest.mock import AsyncMock

from backend.core import llm_client as llm_mod
from backend.core.config import settings


def _fake_message(text: str = "{}", out_tokens: int = 10, stop: str = "end_turn"):
    usage = types.SimpleNamespace(input_tokens=100, output_tokens=out_tokens)
    block = types.SimpleNamespace(text=text)
    return types.SimpleNamespace(content=[block], usage=usage, stop_reason=stop)


@pytest.fixture
def patched_create(monkeypatch):
    """anthropic messages.create 를 가로채 호출 kwargs 를 포착."""
    create = AsyncMock(return_value=_fake_message())
    monkeypatch.setattr(llm_mod.llm_client._client.messages, "create", create)
    return create


@pytest.mark.asyncio
async def test_default_model_used_when_no_override(patched_create):
    await llm_mod.llm_client.call("sys", "user")
    assert patched_create.call_args.kwargs["model"] == settings.LLM_MODEL


@pytest.mark.asyncio
async def test_per_call_model_override(patched_create):
    await llm_mod.llm_client.call("sys", "user", model="claude-sonnet-4-6")
    assert patched_create.call_args.kwargs["model"] == "claude-sonnet-4-6"


@pytest.mark.asyncio
async def test_haiku_ceiling_caps_at_8192(patched_create):
    await llm_mod.llm_client.call("sys", "user", max_tokens=20000)  # 기본=Haiku
    assert patched_create.call_args.kwargs["max_tokens"] == 8192


@pytest.mark.asyncio
async def test_sonnet_ceiling_allows_above_8192(patched_create):
    await llm_mod.llm_client.call("sys", "user", max_tokens=20000, model="claude-sonnet-4-6")
    assert patched_create.call_args.kwargs["max_tokens"] == 20000


# ── 비전 입력 (폴리시 루프 비평자용) ──────────────────────────────────────────
_PNG = b"\x89PNG\r\n\x1a\n\x00\x00fakepngbytes"


@pytest.mark.asyncio
async def test_no_images_keeps_string_content(patched_create):
    """이미지 없으면 기존처럼 content=문자열 (하위호환)."""
    await llm_mod.llm_client.call("sys", "user")
    content = patched_create.call_args.kwargs["messages"][0]["content"]
    assert content == "user"


@pytest.mark.asyncio
async def test_images_build_vision_blocks(patched_create):
    """이미지 주면 content=[image블록…, text블록]; base64·media_type 정확."""
    import base64
    await llm_mod.llm_client.call("sys", "user", images=[_PNG, _PNG])
    content = patched_create.call_args.kwargs["messages"][0]["content"]
    assert isinstance(content, list) and len(content) == 3  # 2 image + 1 text
    for blk in content[:2]:
        assert blk["type"] == "image"
        assert blk["source"]["media_type"] == "image/png"
        assert blk["source"]["data"] == base64.b64encode(_PNG).decode()
    assert content[-1] == {"type": "text", "text": "user"}
