# bridge/routes/mode.py
import logging
from flask import Blueprint, jsonify, request, current_app
from bridge.state import get_state
from bridge.profiles.presets import PRESET_NAMES, load_preset
from bridge.lights.types import Command
import time

logger = logging.getLogger("lumiq")
bp = Blueprint("mode", __name__)

@bp.get("/mode")
def get_mode():
    return jsonify({"mode": get_state().mode})

@bp.post("/mode")
def set_mode():
    data = request.get_json(force=True)
    mode = data.get("mode", "")
    valid = (
        mode == "auto"
        or (mode.startswith("preset:") and mode.split(":")[1] in PRESET_NAMES)
        or mode.startswith("theme:")
    )
    if not valid:
        return jsonify({"error": f"Invalid mode: {mode}"}), 400
    get_state().set_mode(mode)

    # Immediately apply colour when switching to a preset or theme
    if mode != "auto":
        _apply_static_mode(mode)

    return jsonify({"mode": mode})


def _apply_static_mode(mode: str):
    """Look up the profile for this mode and push its first base_color to all devices."""
    try:
        profile = None
        if mode.startswith("preset:"):
            name = mode.split(":", 1)[1]
            profile = load_preset(name)
        elif mode.startswith("theme:"):
            slug = mode.split(":", 1)[1]
            cache = current_app.config.get("cache")
            if cache:
                profile = cache.get("themes", slug)

        if not profile:
            logger.warning("set_mode: no profile found for mode=%s", mode)
            return

        base_colors = profile.get("base_colors", [])
        if not base_colors:
            return
        hex_color = base_colors[0]

        # Energy multiplier drives brightness: chill=0.3 → 30%, party/club=1.0 → 100%
        energy = float(profile.get("energy_multiplier", 0.7))
        brightness = max(10, min(100, int(energy * 100)))

        controller = current_app.config.get("controller")
        room_store = current_app.config.get("room_store")
        if not controller or not room_store:
            return

        now = time.time()
        for device in room_store.get_devices():
            if not device.online:
                continue
            cmd = Command(
                device_id=device.id,
                hex_color=hex_color,
                brightness_pct=brightness,
                at_timestamp=now,
            )
            controller.send_command(cmd)
            logger.info("mode static colour applied device=%s color=%s bright=%d mode=%s",
                        device.id, hex_color, brightness, mode)
    except Exception as e:
        logger.error("_apply_static_mode failed mode=%s error=%s", mode, e)
