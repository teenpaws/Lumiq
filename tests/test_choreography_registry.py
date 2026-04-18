from bridge.choreography.registry import load_registry, filter_eligible
from bridge.lights.types import Device

def make_device(id, x, y, zone):
    return Device(id=id, tuya_id=id, local_key="k", address="192.168.1.1",
                  type="color_bulb", x=x, y=y, zone=zone,
                  latency_ms=40, online=True, capabilities=["rgb"])

def test_load_registry_returns_five_patterns():
    patterns = load_registry()
    assert len(patterns) == 5
    names = {p["name"] for p in patterns}
    assert "wave_lr" in names

def test_single_bulb_only_pulse_and_breathe():
    devices = [make_device("b1", 1.0, 1.0, "center")]
    eligible = filter_eligible(devices, ["wave_lr", "pulse_all", "breathe_all"])
    assert set(eligible) == {"pulse_all", "breathe_all"}

def test_three_bulbs_enables_wave_lr():
    devices = [make_device(f"b{i}", float(i), 1.0, "z") for i in range(3)]
    eligible = filter_eligible(devices, ["wave_lr", "pulse_all"])
    assert "wave_lr" in eligible

def test_four_bulbs_enables_radial():
    devices = [make_device(f"b{i}", float(i % 2), float(i // 2), "z") for i in range(4)]
    eligible = filter_eligible(devices, ["radial", "pulse_all"])
    assert "radial" in eligible

def test_offline_bulbs_not_counted():
    devices = [make_device(f"b{i}", float(i), 1.0, "z") for i in range(3)]
    devices[2].online = False  # only 2 online
    eligible = filter_eligible(devices, ["wave_lr", "pulse_all"])
    assert "wave_lr" not in eligible

def test_preferences_order_preserved():
    devices = [make_device(f"b{i}", float(i), 1.0, "z") for i in range(4)]
    prefs = ["radial", "wave_lr", "pulse_all"]
    eligible = filter_eligible(devices, prefs)
    assert eligible.index("radial") < eligible.index("pulse_all")
