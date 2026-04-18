# bridge/state.py
import threading
from typing import Optional

class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.mode: str = "preset:chill"
        self.active_track_id: Optional[str] = None
        self.active_profile: Optional[dict] = None
        self.last_music_tier: Optional[int] = None
        self.bulb_status: dict = {}

    def set_mode(self, mode: str):
        with self._lock:
            self.mode = mode

    def set_track(self, track_id: str):
        with self._lock:
            self.active_track_id = track_id

    def to_health_dict(self) -> dict:
        with self._lock:
            return {
                "mode": self.mode,
                "active_track_id": self.active_track_id,
                "last_music_tier": self.last_music_tier,
                "bulb_status": dict(self.bulb_status),
            }

_state = AppState()

def get_state() -> AppState:
    return _state
