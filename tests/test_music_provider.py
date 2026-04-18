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

# --- append to existing tests/test_music_provider.py ---
from bridge.music.third_party import ThirdPartyProvider
from bridge.music.microphone import MicrophoneProvider
from bridge.music.provider import chain

MOCK_GETSONGBPM = {
    "search": [{"song_title": "Test Song", "tempo": "120", "artist": {"name": "Test"}}]
}

def test_third_party_returns_audio_features(requests_mock):
    requests_mock.get(
        "https://api.getsongbpm.com/search/",
        json=MOCK_GETSONGBPM,
    )
    provider = ThirdPartyProvider(api_key="test_key")
    result = provider.fetch("track123", title="Test Song", artist="Test")
    assert isinstance(result, AudioFeatures)
    assert result.bpm == 120.0
    assert result.source_tier == 2

def test_third_party_returns_none_on_empty_results(requests_mock):
    requests_mock.get("https://api.getsongbpm.com/search/", json={"search": []})
    provider = ThirdPartyProvider(api_key="test_key")
    result = provider.fetch("track123", title="Unknown", artist="Unknown")
    assert result is None

def test_chain_falls_through_to_tier2(mocker):
    p1 = mocker.MagicMock()
    p1.fetch.return_value = None
    p2 = mocker.MagicMock()
    p2.fetch.return_value = AudioFeatures(
        bpm=120.0, energy=0.7, valence=0.5, mood_tag="calm",
        beat_grid=[], source_tier=2
    )
    result = chain([p1, p2], "track123", access_token="tok")
    assert result.source_tier == 2
    p1.fetch.assert_called_once()
    p2.fetch.assert_called_once()

def test_chain_returns_none_when_all_fail(mocker):
    providers = [mocker.MagicMock() for _ in range(3)]
    for p in providers:
        p.fetch.return_value = None
    result = chain(providers, "track123")
    assert result is None

def test_microphone_provider_returns_audio_features(mocker):
    import numpy as np
    fake_audio = np.zeros((22050, 1), dtype="float32")
    mocker.patch("bridge.music.microphone.sd.rec", return_value=fake_audio)
    mocker.patch("bridge.music.microphone.sd.wait")
    mocker.patch("bridge.music.microphone.librosa.beat.beat_track",
                 return_value=(128.0, np.array([11, 22, 33])))
    mocker.patch("bridge.music.microphone.librosa.frames_to_time",
                 return_value=np.array([0.5, 1.0, 1.5]))
    provider = MicrophoneProvider(record_duration=1)
    result = provider.fetch("any_track_id")
    assert isinstance(result, AudioFeatures)
    assert result.bpm == 128.0
    assert result.source_tier == 3
