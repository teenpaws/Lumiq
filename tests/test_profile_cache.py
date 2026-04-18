import pytest
from bridge.profiles.cache import ProfileCache

SAMPLE_PROFILE = {
    "profile_name": "club", "source": "preset", "base_colors": ["#ff0000"],
    "transition_speed_ms": 200, "beat_response": "strobe", "energy_multiplier": 1.0,
    "mood_tag": "high_energy", "pattern_preferences": ["pulse_all"],
    "composition_rule": "last_write_wins", "created_at": "2026-04-18T00:00:00Z"
}

@pytest.fixture
def cache(tmp_path):
    return ProfileCache(str(tmp_path))

def test_miss_returns_none(cache):
    assert cache.get("tracks", "nonexistent") is None

def test_put_and_get(cache):
    cache.put("themes", "tokyo_rain", SAMPLE_PROFILE)
    loaded = cache.get("themes", "tokyo_rain")
    assert loaded["profile_name"] == "club"

def test_list_empty(cache):
    assert cache.list("tracks") == []

def test_list_after_put(cache):
    cache.put("tracks", "track_abc", SAMPLE_PROFILE)
    cache.put("tracks", "track_def", SAMPLE_PROFILE)
    names = cache.list("tracks")
    assert sorted(names) == ["track_abc", "track_def"]

def test_put_validates_profile(cache):
    with pytest.raises(ValueError):
        cache.put("tracks", "bad", {"profile_name": "incomplete"})
