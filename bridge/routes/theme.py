# bridge/routes/theme.py
import re
from flask import Blueprint, jsonify, request, current_app
from bridge.choreography.registry import load_registry

bp = Blueprint("theme", __name__)

@bp.post("/theme")
def generate_theme():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "").strip()
    if len(prompt) < 3 or len(prompt) > 200:
        return jsonify({"error": "Prompt must be 3\u2013200 characters"}), 400

    slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:50].strip("_")
    cache = current_app.config["cache"]
    existing = cache.get("themes", slug)
    if existing:
        return jsonify({"profile": existing, "cached": True})

    claude = current_app.config["claude"]
    room_store = current_app.config["room_store"]
    registry = [p["name"] for p in load_registry()]
    room_profile = {
        "floor_plan": room_store.get_floor_plan(),
        "devices": [d.__dict__ for d in room_store.get_devices()],
    }
    profile = claude.generate_theme_profile(prompt, room_profile, registry)
    cache.put("themes", slug, profile)
    return jsonify({"profile": profile, "cached": False, "slug": slug})
