from backend.core import config, crypto


def _set_key(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", Fernet.generate_key().decode())


def test_encrypt_decrypt_roundtrip(monkeypatch):
    _set_key(monkeypatch)
    secret = "IGQVJ...long-lived-token"
    enc = crypto.encrypt(secret)
    assert enc != secret                  # 암호문은 원문과 다르다
    assert crypto.decrypt(enc) == secret  # 왕복 복원


def test_enabled_reflects_key(monkeypatch):
    monkeypatch.setattr(config.settings, "SOCIAL_TOKEN_KEY", "")
    assert crypto.enabled() is False
    _set_key(monkeypatch)
    assert crypto.enabled() is True
