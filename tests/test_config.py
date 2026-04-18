import os
from bridge.config import Config


def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    monkeypatch.setenv("BRIDGE_PORT", "6000")
    monkeypatch.setenv("USE_SPOTIFY_FEATURES", "false")
    cfg = Config.from_env()
    assert cfg.claude_api_key == "test-key"
    assert cfg.bridge_port == 6000
    assert cfg.use_spotify_features is False


def test_config_defaults(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "x")
    cfg = Config.from_env()
    assert cfg.bridge_port == 5000
    assert cfg.use_spotify_features is True
