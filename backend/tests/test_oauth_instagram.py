from backend.core import config, oauth


def test_authorize_url_has_scope_state(monkeypatch):
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "cid")
    url = oauth.instagram_authorize_url("st8")
    assert url.startswith("https://www.instagram.com/oauth/authorize")   # m4: host 검증
    assert "instagram_business_content_publish" in url
    assert "state=st8" in url
    assert "client_id=cid" in url


def test_enabled(monkeypatch):
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "")
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_SECRET", "")
    assert oauth.instagram_enabled() is False
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "c")
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_SECRET", "s")
    assert oauth.instagram_enabled() is True


async def test_exchange_returns_account(monkeypatch, respx_mock):
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_ID", "cid")
    monkeypatch.setattr(config.settings, "INSTAGRAM_CLIENT_SECRET", "sec")
    respx_mock.post("https://api.instagram.com/oauth/access_token").respond(
        json={"access_token": "SHORT", "user_id": "ig123"})
    respx_mock.get("https://graph.instagram.com/access_token").respond(
        json={"access_token": "LONG", "expires_in": 5184000})
    respx_mock.get("https://graph.instagram.com/me").respond(
        json={"user_id": "ig123", "username": "myshop"})
    acct = await oauth.instagram_exchange("CODE")
    assert acct["ig_user_id"] == "ig123"
    assert acct["access_token"] == "LONG"
    assert acct["ig_username"] == "myshop"
    assert acct["expires_in"] == 5184000
