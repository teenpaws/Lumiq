from typing import List, Literal

BEAT_RESPONSES = {"breathe", "pulse", "sweep", "strobe", "none"}
SOURCES = {"preset", "theme", "auto_track"}


def validate_profile(p: dict) -> dict:
    required = {"profile_name", "source", "base_colors", "transition_speed_ms",
                "beat_response", "energy_multiplier", "mood_tag",
                "pattern_preferences", "composition_rule"}
    missing = required - p.keys()
    if missing:
        raise ValueError(f"Profile missing fields: {missing}")
    if p["beat_response"] not in BEAT_RESPONSES:
        raise ValueError(f"Invalid beat_response: {p['beat_response']}")
    if p["source"] not in SOURCES:
        raise ValueError(f"Invalid source: {p['source']}")
    return p
