from bridge.lights.types import Device, Command
from bridge.music.types import AudioFeatures, BeatEvent
from bridge.profiles.types import validate_profile
import pytest


def test_device_fields():
    d = Device(id="b1", tuya_id="abc", local_key="xyz", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    assert d.latency_ms == 40


def test_validate_profile_missing_field():
    with pytest.raises(ValueError, match="missing fields"):
        validate_profile({"profile_name": "x"})


def test_validate_profile_ok():
    p = {
        "profile_name": "test", "source": "preset", "base_colors": ["#ff0000"],
        "transition_speed_ms": 500, "beat_response": "pulse", "energy_multiplier": 0.8,
        "mood_tag": "energetic", "pattern_preferences": ["pulse_all"],
        "composition_rule": "last_write_wins"
    }
    assert validate_profile(p) == p
