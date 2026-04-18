import math
from typing import List
from bridge.lights.types import Device, Command

_BUFFER_S = 0.05  # 50ms pre-send buffer

def _compensation(device: Device, beat_time: float) -> float:
    return beat_time - (device.latency_ms / 1000.0) - _BUFFER_S

def _pick_color(profile: dict, index: int = 0) -> str:
    colors = profile.get("base_colors", ["#ffffff"])
    return colors[index % len(colors)]

def compute_commands(
    pattern: str,
    devices: List[Device],
    beat_time: float,
    profile: dict,
) -> List[Command]:
    online = [d for d in devices if d.online]
    if pattern == "pulse_all":
        return _pulse_all(online, beat_time, profile)
    if pattern == "breathe_all":
        return _breathe_all(online, beat_time, profile)
    if pattern == "wave_lr":
        return _wave_lr(online, beat_time, profile)
    if pattern == "alternate_zones":
        return _alternate_zones(online, beat_time, profile)
    if pattern == "radial":
        return _radial(online, beat_time, profile)
    return []

def _pulse_all(devices, beat_time, profile):
    color = _pick_color(profile)
    brightness = int(100 * profile.get("energy_multiplier", 0.8))
    return [Command(
        device_id=d.id,
        hex_color=color,
        brightness_pct=brightness,
        at_timestamp=_compensation(d, beat_time),
    ) for d in devices]

def _breathe_all(devices, beat_time, profile):
    brightness = int(60 * profile.get("energy_multiplier", 0.6))
    color = _pick_color(profile, 1)
    return [Command(
        device_id=d.id,
        hex_color=color,
        brightness_pct=brightness,
        at_timestamp=_compensation(d, beat_time),
    ) for d in devices]

def _wave_lr(devices, beat_time, profile):
    sorted_devices = sorted(devices, key=lambda d: d.x)
    n = len(sorted_devices)
    beat_duration = profile.get("transition_speed_ms", 500) / 1000.0
    cmds = []
    for i, d in enumerate(sorted_devices):
        stagger = (i / max(n - 1, 1)) * beat_duration
        color = _pick_color(profile, i)
        brightness = int(100 * profile.get("energy_multiplier", 0.8))
        cmds.append(Command(
            device_id=d.id,
            hex_color=color,
            brightness_pct=brightness,
            at_timestamp=_compensation(d, beat_time) + stagger,
        ))
    return cmds

def _alternate_zones(devices, beat_time, profile):
    zones = sorted({d.zone for d in devices})
    cmds = []
    beat_index = int(beat_time) % 2
    for d in devices:
        zone_index = zones.index(d.zone)
        is_active = (zone_index % 2) == beat_index
        brightness = int(90 * profile.get("energy_multiplier", 0.8)) if is_active else 15
        color = _pick_color(profile, zone_index)
        cmds.append(Command(
            device_id=d.id,
            hex_color=color,
            brightness_pct=brightness,
            at_timestamp=_compensation(d, beat_time),
        ))
    return cmds

def _radial(devices, beat_time, profile):
    cx = sum(d.x for d in devices) / len(devices)
    cy = sum(d.y for d in devices) / len(devices)
    max_dist = max(math.sqrt((d.x - cx) ** 2 + (d.y - cy) ** 2) for d in devices) or 1.0
    beat_duration = profile.get("transition_speed_ms", 500) / 1000.0
    cmds = []
    for d in devices:
        dist = math.sqrt((d.x - cx) ** 2 + (d.y - cy) ** 2)
        stagger = (dist / max_dist) * beat_duration
        brightness = int(100 * profile.get("energy_multiplier", 0.8))
        cmds.append(Command(
            device_id=d.id,
            hex_color=_pick_color(profile),
            brightness_pct=brightness,
            at_timestamp=_compensation(d, beat_time) + stagger,
        ))
    return cmds
