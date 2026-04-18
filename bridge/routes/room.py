# bridge/routes/room.py
from flask import Blueprint, jsonify, request, current_app
from bridge.lights.types import Device

bp = Blueprint("room", __name__)

@bp.get("/room")
def get_room():
    room_store = current_app.config["room_store"]
    devices = room_store.get_devices()
    return jsonify({
        "floor_plan": room_store.get_floor_plan(),
        "devices": [d.__dict__ for d in devices],
    })

@bp.post("/room")
def save_room():
    room_store = current_app.config["room_store"]
    data = request.get_json(force=True)
    devices = [Device(**d) for d in data["devices"]]
    room_store.save(data["floor_plan"], devices)
    current_app.config["controller"].update_devices(devices)
    current_app.config["choreo"].update_devices(devices)
    return jsonify({"saved": True, "device_count": len(devices)})

@bp.post("/room/blink/<device_id>")
def blink(device_id):
    controller = current_app.config["controller"]
    try:
        controller.blink(device_id)
        return jsonify({"blinked": device_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/room/calibrate")
def calibrate():
    room_store = current_app.config["room_store"]
    controller = current_app.config["controller"]
    results = {}
    for device in room_store.get_devices():
        try:
            latency_ms = controller.measure_latency(device.id)
            room_store.update_device(device.id, latency_ms=latency_ms)
            results[device.id] = latency_ms
        except Exception as e:
            results[device.id] = f"error: {e}"
    return jsonify({"latencies_ms": results})
