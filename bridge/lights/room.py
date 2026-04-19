import json
import os
from typing import List, Optional
from bridge.lights.types import Device


class RoomStore:
    def __init__(self, path: str):
        self._path = path
        self._floor_plan: dict = {}
        self._devices: List[Device] = []
        if os.path.exists(path):
            self._load()

    def _load(self):
        with open(self._path) as f:
            data = json.load(f)
        self._floor_plan = data.get("floor_plan", {})
        self._devices = [Device(**d) for d in data.get("devices", [])]

    def save(self, floor_plan: dict, devices: List[Device]):
        self._floor_plan = floor_plan
        self._devices = devices
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w") as f:
            json.dump({
                "floor_plan": floor_plan,
                "devices": [d.__dict__ for d in devices],
            }, f, indent=2)

    def get_devices(self) -> List[Device]:
        return list(self._devices)

    def get_device(self, id: str) -> Optional[Device]:
        return next((d for d in self._devices if d.id == id), None)

    def update_device(self, id: str, **kwargs):
        device = self.get_device(id)
        if device is None:
            raise KeyError(f"Device {id} not found")
        for k, v in kwargs.items():
            setattr(device, k, v)
        self.save(self._floor_plan, self._devices)

    def get_floor_plan(self) -> dict:
        return self._floor_plan

    # ── Named room profiles ──────────────────────────────────────────────────

    def _rooms_dir(self) -> str:
        base = os.path.dirname(self._path) or "."
        return os.path.join(base, "rooms")

    def list_rooms(self) -> list:
        d = self._rooms_dir()
        if not os.path.exists(d):
            return []
        return [f[:-5] for f in os.listdir(d) if f.endswith(".json")]

    def save_named(self, name: str):
        """Save current room config under a named profile."""
        d = self._rooms_dir()
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, f"{name}.json"), "w") as f:
            json.dump({
                "floor_plan": self._floor_plan,
                "devices": [dev.__dict__ for dev in self._devices],
            }, f, indent=2)

    def load_named(self, name: str):
        """Load a named room profile as the active room."""
        path = os.path.join(self._rooms_dir(), f"{name}.json")
        if not os.path.exists(path):
            raise KeyError(f"Room profile '{name}' not found")
        with open(path) as f:
            data = json.load(f)
        self.save(data["floor_plan"], [Device(**d) for d in data["devices"]])
