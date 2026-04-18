# bridge/routes/track.py
import logging
from flask import Blueprint, jsonify, request, current_app
from bridge.music.types import AudioFeatures, BeatEvent
from bridge.music.provider import chain as provider_chain
from bridge.profiles.presets import load_preset
from bridge.choreography.registry import load_registry
from bridge.state import get_state

bp = Blueprint("track", __name__)
logger = logging.getLogger("lumiq")

@bp.post("/track")
def track_change():
    data = request.get_json(force=True)
    track_id = data.get("track_id", "")
    position_ms = data.get("position_ms", 0)
    is_playing = data.get("is_playing", True)
    access_token = data.get("access_token", "")

    if not is_playing:
        current_app.config["choreo"].stop()
        return jsonify({"status": "paused"})

    state = get_state()
    state.set_track(track_id)
    cache = current_app.config["cache"]
    claude = current_app.config["claude"]
    choreo = current_app.config["choreo"]
    room_store = current_app.config["room_store"]
    providers = current_app.config["providers"]
    mode = state.mode
    features: AudioFeatures | None = None

    profile = None
    if mode.startswith("preset:"):
        preset_name = mode.split(":", 1)[1]
        profile = load_preset(preset_name)
    elif mode.startswith("theme:"):
        slug = mode.split(":", 1)[1]
        profile = cache.get("themes", slug)
    else:  # auto
        profile = cache.get("tracks", track_id)
        features = provider_chain(providers, track_id, access_token=access_token)
        if features:
            state.last_music_tier = features.source_tier
        if profile is None and features:
            registry = [p["name"] for p in load_registry()]
            room_profile = {
                "floor_plan": room_store.get_floor_plan(),
                "devices": [d.__dict__ for d in room_store.get_devices()],
            }
            try:
                profile = claude.generate_auto_profile(features, room_profile, registry)
                cache.put("tracks", track_id, profile)
            except Exception as e:
                logger.error("Claude auto profile error: %s", e)

    if profile is None:
        profile = load_preset("chill")

    state.active_profile = profile

    if features and features.beat_grid:
        choreo.play_with_position(features, profile, position_ms / 1000.0)
    else:
        choreo.play_with_position(
            _synthetic_beat_features(profile.get("transition_speed_ms", 500)),
            profile,
            position_ms / 1000.0,
        )

    logger.info("track mode=%s track_id=%s profile=%s tier=%s",
                mode, track_id, profile.get("profile_name"), state.last_music_tier)
    return jsonify({"status": "playing", "profile": profile.get("profile_name")})

def _synthetic_beat_features(transition_ms: int) -> AudioFeatures:
    beat_interval = transition_ms / 1000.0
    beats = [
        BeatEvent(start=i * beat_interval, duration=beat_interval, confidence=1.0)
        for i in range(240)
    ]
    return AudioFeatures(
        bpm=60000 / transition_ms, energy=0.7, valence=0.5,
        mood_tag="synthetic", beat_grid=beats, source_tier=0,
    )
