# tests/test_music_provider.py
import pytest
from bridge.music.spotify import SpotifyProvider
from bridge.music.types import AudioFeatures

MOCK_FEATURES = {
    "tempo": 128.0, "energy": 0.9, "valence": 0.7,
    "danceability": 0.85, "id": "track123"
}
MOCK_ANALYSIS = {
    "beats": [
        {"start": 0.5, "duration": 0.47, "confidence": 0.9},
        {"start": 0.97, "duration": 0.47, "confidence": 0.85},
        {"start": 1.44, "duration": 0.47, "confidence": 0.95},
    ]
}

def test_spotify_returns_audio_features(requests_mock):
    requests_mock.get(
        "https://api.spotify.com/v1/audio-features/track123",
        json=MOCK_FEATURES,
    )
    requests_mock.get(
        "https://api.spotify.com/v1/audio-analysis/track123",
        json=MOCK_ANALYSIS,
    )
    provider = SpotifyProvider()
    result = provider.fetch("track123", access_token="fake_token")
    assert isinstance(result, AudioFeatures)
    assert result.bpm == 128.0
    assert result.energy == 0.9
    assert len(result.beat_grid) == 3
    assert result.source_tier == 1

def test_spotify_returns_none_on_403(requests_mock):
    requests_mock.get(
        "https://api.spotify.com/v1/audio-features/track123",
        status_code=403,
    )
    provider = SpotifyProvider()
    result = provider.fetch("track123", access_token="fake_token")
    assert result is None
