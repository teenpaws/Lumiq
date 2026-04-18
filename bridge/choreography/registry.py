import json
import os
from typing import List
from bridge.lights.types import Device

_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "patterns.json")

def load_registry() -> List[dict]:
    with open(os.path.normpath(_REGISTRY_PATH)) as f:
        return json.load(f)

def filter_eligible(devices: List[Device], pattern_preferences: List[str]) -> List[str]:
    online_devices = [d for d in devices if d.online]
    registry = {p["name"]: p for p in load_registry()}
    eligible = []
    for pref in pattern_preferences:
        if pref not in registry:
            continue
        pattern = registry[pref]
        if len(online_devices) < pattern["min_bulbs"]:
            continue
        reqs_met = True
        for req in pattern["requires"]:
            if req == "x_coords" and not all(hasattr(d, "x") for d in online_devices):
                reqs_met = False
            if req == "y_coords" and not all(hasattr(d, "y") for d in online_devices):
                reqs_met = False
            if req == "zones" and not all(d.zone for d in online_devices):
                reqs_met = False
        if reqs_met:
            eligible.append(pref)
    return eligible
