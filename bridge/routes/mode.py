# bridge/routes/mode.py
from flask import Blueprint, jsonify, request
from bridge.state import get_state
from bridge.profiles.presets import PRESET_NAMES

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
    return jsonify({"mode": mode})
