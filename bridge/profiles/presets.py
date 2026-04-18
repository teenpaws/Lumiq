# bridge/profiles/presets.py
import json
import os
from typing import Optional

_PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "profiles", "presets")
PRESET_NAMES = {"club", "lounge", "party", "chill", "concert"}

def load_preset(name: str) -> Optional[dict]:
    if name not in PRESET_NAMES:
        return None
    path = os.path.normpath(os.path.join(_PRESETS_DIR, f"{name}.json"))
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
