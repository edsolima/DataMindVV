import os
import pytest
from utils.config_manager import ConfigManager

def test_encryption_key_generation(monkeypatch, tmp_path):
    # Força uso de diretório temporário para .env
    env_file = tmp_path / ".env"
    monkeypatch.setenv("ENCRYPTION_KEY", "")
    cm = ConfigManager()
    key = cm._get_or_create_encryption_key()
    assert key is not None
    assert isinstance(key, bytes)

def test_password_encryption_decryption():
    cm = ConfigManager()
    senha = "minha_senha_supersecreta"
    encrypted = cm.encrypt_password(senha)
    assert encrypted != senha
    decrypted = cm.decrypt_password(encrypted)
    assert decrypted == senha 