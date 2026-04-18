import json
import os
from typing import Optional, List
from bridge.profiles.types import validate_profile


class ProfileCache:
    def __init__(self, base_dir: str):
        self._base = base_dir
        for sub in ("presets", "themes", "tracks"):
            os.makedirs(os.path.join(base_dir, sub), exist_ok=True)

    def _path(self, source: str, name: str) -> str:
        return os.path.join(self._base, source, f"{name}.json")

    def get(self, source: str, name: str) -> Optional[dict]:
        p = self._path(source, name)
        if not os.path.exists(p):
            return None
        with open(p) as f:
            return json.load(f)

    def put(self, source: str, name: str, profile: dict):
        validate_profile(profile)
        with open(self._path(source, name), "w") as f:
            json.dump(profile, f, indent=2)

    def list(self, source: str) -> List[str]:
        d = os.path.join(self._base, source)
        return [f[:-5] for f in os.listdir(d) if f.endswith(".json")]
