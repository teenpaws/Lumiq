import pytest
from bridge.choreography.patterns import compute_commands
from bridge.lights.types import Device, Command

def make_device(id, x, y, zone, latency_ms=40):
    return Device(id=id, tuya_id=id, local_key="k", address="192.168.1.1",
                  type="color_bulb", x=x, y=y, zone=zone,
                  latency_ms=latency_ms, online=True, capabilities=["rgb"])

PROFILE = {
    "base_colors": ["#ff0000", "#0000ff", "#00ff00"],
    "beat_response": "pulse",
    "energy_multiplier": 0.8,
    "transition_speed_ms": 400,
}
BEAT_TIME = 100.0  # unix timestamp

def test_pulse_all_fires_all_devices_simultaneously():
    devices = [make_device("b1", 0.0, 0.0, "fl"), make_device("b2", 1.0, 0.0, "fr")]
    cmds = compute_commands("pulse_all", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 2
    assert cmds[0].hex_color == cmds[1].hex_color

def test_pulse_all_applies_latency_compensation():
    d1 = make_device("b1", 0.0, 0.0, "fl", latency_ms=40)
    d2 = make_device("b2", 1.0, 0.0, "fr", latency_ms=80)
    cmds = compute_commands("pulse_all", [d1, d2], BEAT_TIME, PROFILE)
    cmd1 = next(c for c in cmds if c.device_id == "b1")
    cmd2 = next(c for c in cmds if c.device_id == "b2")
    # b2 has higher latency so its command should be scheduled earlier
    assert cmd2.at_timestamp < cmd1.at_timestamp

def test_wave_lr_staggers_by_x_position():
    devices = [
        make_device("b1", 0.0, 0.0, "fl"),  # leftmost
        make_device("b2", 1.0, 0.0, "fm"),  # middle
        make_device("b3", 2.0, 0.0, "fr"),  # rightmost
    ]
    cmds = compute_commands("wave_lr", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 3
    by_device = {c.device_id: c.at_timestamp for c in cmds}
    assert by_device["b1"] <= by_device["b2"] <= by_device["b3"]

def test_breathe_all_returns_all_devices():
    devices = [make_device(f"b{i}", float(i), 0.0, "z") for i in range(4)]
    cmds = compute_commands("breathe_all", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 4

def test_alternate_zones_splits_by_zone():
    devices = [
        make_device("b1", 0.0, 0.0, "front"),
        make_device("b2", 1.0, 0.0, "front"),
        make_device("b3", 0.0, 1.0, "back"),
        make_device("b4", 1.0, 1.0, "back"),
    ]
    cmds = compute_commands("alternate_zones", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 4
    bright_cmds = [c for c in cmds if c.brightness_pct > 50]
    dim_cmds = [c for c in cmds if c.brightness_pct <= 50]
    assert len(bright_cmds) == 2
    assert len(dim_cmds) == 2
