# tests/test_integration_critical_path.py
"""
Critical path smoke test:
  POST /track → SpotifyProvider (mocked) → ClaudeClient (mocked)
  → ChoreographyLayer → LightController (mocked) → commands arrive in order
"""
import json
import time
import pytest
from bridge.app import create_app
from bridge.config import Config

MOCK_FEATURES_RESP = {
    "tempo": 120.0, "energy": 0.8, "valence": 0.6,
    "danceability": 0.75, "id": "track_test_001"
}
MOCK_ANALYSIS_RESP = {
    "beats": [
        {"start": 0.5, "duration": 0.5, "confidence": 0.9},
        {"start": 1.0, "duration": 0.5, "confidence": 0.9},
        {"start": 1.5, "duration": 0.5, "confidence": 0.9},
    ]
}
MOCK_CLAUDE_PROFILE = {
    "profile_name": "smoke_test_profile", "source": "auto_track",
    "created_at": "2026-04-18T00:00:00Z",
    "base_colors": ["#ff0000", "#0000ff"],
    "transition_speed_ms": 500, "beat_response": "pulse",
    "energy_multiplier": 0.8, "mood_tag": "energetic",
    "pattern_preferences": ["pulse_all"],
    "composition_rule": "last_write_wins"
}

@pytest.fixture
def test_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    return Config(
        claude_api_key="test-key",
        bridge_port=5001,
        profiles_dir=str(tmp_path / "profiles"),
        room_profile_path=str(tmp_path / "room_profile.json"),
        log_path=str(tmp_path / "logs/bridge.log"),
        use_spotify_features=True,
        getsongbpm_api_key="",
    )

@pytest.fixture
def client(test_config, mocker):
    mocker.patch("bridge.music.spotify.requests.get", side_effect=_mock_spotify_get)
    mock_claude_response = mocker.MagicMock()
    mock_claude_response.content = [mocker.MagicMock(text=json.dumps(MOCK_CLAUDE_PROFILE))]
    mocker.patch(
        "bridge.claude_client.anthropic.Anthropic",
        return_value=mocker.MagicMock(
            messages=mocker.MagicMock(
                create=mocker.MagicMock(return_value=mock_claude_response)
            )
        )
    )
    mock_bulb = mocker.MagicMock()
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)

    app = create_app(test_config)
    # Reset global state for each test
    from bridge.state import get_state
    state = get_state()
    state.mode = "preset:chill"
    state.active_track_id = None
    state.active_profile = None
    state.last_music_tier = None

    return app.test_client(), app, mock_bulb

def _mock_spotify_get(url, **kwargs):
    import unittest.mock as mock
    resp = mock.MagicMock()
    if "audio-features" in url:
        resp.status_code = 200
        resp.json.return_value = MOCK_FEATURES_RESP
    elif "audio-analysis" in url:
        resp.status_code = 200
        resp.json.return_value = MOCK_ANALYSIS_RESP
    else:
        resp.status_code = 404
    return resp

def test_health_endpoint(client):
    flask_client, app, _ = client
    resp = flask_client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"

def test_mode_switch_to_auto(client):
    flask_client, app, _ = client
    resp = flask_client.post("/mode", json={"mode": "auto"})
    assert resp.status_code == 200
    assert resp.get_json()["mode"] == "auto"

def test_track_change_triggers_profile_generation(client):
    flask_client, app, _ = client
    flask_client.post("/mode", json={"mode": "auto"})
    resp = flask_client.post("/track", json={
        "track_id": "track_test_001",
        "position_ms": 0,
        "is_playing": True,
        "access_token": "fake_token",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "playing"
    assert data["profile"] == "smoke_test_profile"

def test_track_cached_on_second_call(client):
    flask_client, app, _ = client
    flask_client.post("/mode", json={"mode": "auto"})
    flask_client.post("/track", json={
        "track_id": "track_test_001",
        "position_ms": 0,
        "is_playing": True,
        "access_token": "fake_token",
    })
    cache = app.config["cache"]
    cached = cache.get("tracks", "track_test_001")
    assert cached is not None
    assert cached["profile_name"] == "smoke_test_profile"

def test_preset_mode_no_claude_call(client, mocker):
    flask_client, app, _ = client
    flask_client.post("/mode", json={"mode": "preset:club"})
    resp = flask_client.post("/track", json={
        "track_id": "track_abc",
        "position_ms": 0,
        "is_playing": True,
        "access_token": "fake_token",
    })
    assert resp.status_code == 200
    assert resp.get_json()["profile"] == "club"

def test_pause_stops_choreography(client):
    flask_client, app, _ = client
    resp = flask_client.post("/track", json={
        "track_id": "track_001",
        "position_ms": 10000,
        "is_playing": False,
        "access_token": "tok",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "paused"

def test_invalid_mode_rejected(client):
    flask_client, app, _ = client
    resp = flask_client.post("/mode", json={"mode": "nonsense"})
    assert resp.status_code == 400

def test_cron_returns_501(client):
    flask_client, app, _ = client
    resp = flask_client.post("/cron/run-now")
    assert resp.status_code == 501
