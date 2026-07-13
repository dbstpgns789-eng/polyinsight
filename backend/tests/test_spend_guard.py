# -*- coding: utf-8 -*-
"""스펜드 가드 — 쿼터는 원가를 알아야 한다.

실측(2026-07-13, 크레딧 $22 소진): 덱 1건 원가 = $0.51(저작만) ~ $1.91(비전 2R) ~ $3.39(Best-of-3).
그런데 인증 유저 쿼터가 **일 20덱**이었다 → 유저 1명이 하루 **$38**을 태울 수 있다.
크레딧 $22가 반나절에 증발한다. **쿼터가 원가를 몰랐다.**

전역 일일 캡이 진짜 방어선이다 — 유저 수가 늘어도 총액이 캡된다.
"""
import pytest

from backend.core import ratelimit as R
from backend.core.config import settings


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    R._hits.clear()
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    yield
    R._hits.clear()


def _user(uid=1, verified=True):
    return {"id": uid, "email_verified": 1 if verified else 0}


def test_user_daily_quota_is_cost_aware(monkeypatch):
    """유저 쿼터가 원가 기준이어야 한다 — 20덱/일($38)은 크레딧을 반나절에 태운다."""
    assert settings.UPLOAD_USER_LIMIT <= 5, (
        f"인증 유저 일일 {settings.UPLOAD_USER_LIMIT}덱 = 최대 "
        f"${settings.UPLOAD_USER_LIMIT * 1.91:.0f}/일 — 원가를 모르는 쿼터"
    )
    assert settings.UPLOAD_UNVERIFIED_LIMIT <= 2


def test_global_daily_cap_blocks_when_exhausted(monkeypatch):
    """★전역 캡 — 유저가 여럿이어도 하루 총액이 캡된다(진짜 방어선)."""
    monkeypatch.setattr(settings, "GLOBAL_DAILY_DECK_LIMIT", 3)
    for uid in (1, 2, 3):                       # 서로 다른 유저 3명이 1건씩
        R.enforce_upload_quota(_user(uid))
    with pytest.raises(Exception) as e:          # 4번째 유저는 전역 캡에 막힘
        R.enforce_upload_quota(_user(4))
    assert "429" in str(e.value.status_code)


def test_global_cap_zero_means_unlimited(monkeypatch):
    """0이면 전역 캡 없음(로컬 개발·테스트용)."""
    monkeypatch.setattr(settings, "GLOBAL_DAILY_DECK_LIMIT", 0)
    for uid in range(1, 30):
        R.enforce_upload_quota(_user(uid))       # 예외 없이 통과


def test_user_quota_still_applies_under_global_cap(monkeypatch):
    """전역 캡이 넉넉해도 유저 쿼터는 따로 작동한다."""
    monkeypatch.setattr(settings, "GLOBAL_DAILY_DECK_LIMIT", 100)
    monkeypatch.setattr(settings, "UPLOAD_USER_LIMIT", 2)
    R.enforce_upload_quota(_user(7))
    R.enforce_upload_quota(_user(7))
    with pytest.raises(Exception):
        R.enforce_upload_quota(_user(7))
