# tests/test_claude_client.py
import json, pytest
from bridge.claude_client import ClaudeClient
from bridge.music.types import AudioFeatures

SAMPLE_FEATURES = AudioFeatures(
    bpm=128.0, energy=0.9, valence=0.7, mood_tag="high_energy_positive",
    beat_grid=[], source_tier=1
)
SAMPLE_PROFILE = {
    "profile_name": "energetic_dance", "source": "auto_track",
    "created_at": "2026-04-18T00:00:00Z", "base_colors": ["#ff0080", "#00ffff"],
    "transition_speed_ms": 300, "beat_response": "pulse", "energy_multiplier": 0.9,
    "mood_tag": "high_energy_positive", "pattern_preferences": ["wave_lr", "pulse_all"],
    "composition_rule": "last_write_wins"
}
ROOM_PROFILE = {"floor_plan": {"width_m": 4.0, "length_m": 3.0}, "devices": []}

def test_generate_auto_profile_returns_valid_profile(mocker):
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text=json.dumps(SAMPLE_PROFILE))]
    mock_client.messages.create.return_value = mock_response
    mocker.patch("bridge.claude_client.anthropic.Anthropic", return_value=mock_client)

    client = ClaudeClient(api_key="test")
    result = client.generate_auto_profile(SAMPLE_FEATURES, ROOM_PROFILE, ["pulse_all", "wave_lr"])
    assert result["beat_response"] == "pulse"
    assert result["source"] == "auto_track"

def test_generate_theme_profile_returns_valid_profile(mocker):
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text=json.dumps({**SAMPLE_PROFILE, "source": "theme"}))]
    mock_client.messages.create.return_value = mock_response
    mocker.patch("bridge.claude_client.anthropic.Anthropic", return_value=mock_client)

    client = ClaudeClient(api_key="test")
    result = client.generate_theme_profile("late night tokyo rain", ROOM_PROFILE, ["pulse_all"])
    assert result["source"] == "theme"

def test_invalid_json_response_raises(mocker):
    mock_client = mocker.MagicMock()
    mock_response = mocker.MagicMock()
    mock_response.content = [mocker.MagicMock(text="not json")]
    mock_client.messages.create.return_value = mock_response
    mocker.patch("bridge.claude_client.anthropic.Anthropic", return_value=mock_client)

    client = ClaudeClient(api_key="test")
    with pytest.raises(ValueError, match="Invalid profile JSON"):
        client.generate_auto_profile(SAMPLE_FEATURES, ROOM_PROFILE, ["pulse_all"])
