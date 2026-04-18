# bridge/routes/health.py
from flask import Blueprint, jsonify, current_app
from bridge.state import get_state

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    state = get_state()
    room_store = current_app.config["room_store"]
    devices = room_store.get_devices()
    return jsonify({
        "status": "ok",
        "devices_total": len(devices),
        "devices_online": sum(1 for d in devices if d.online),
        **state.to_health_dict(),
    })
