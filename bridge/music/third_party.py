# bridge/music/third_party.py
import logging
from typing import Optional
import requests
from bridge.music.provider import MusicDataProvider
from bridge.music.types import AudioFeatures, BeatEvent

logger = logging.getLogger("lumiq")

_SEARCH_URL = "https://api.getsongbpm.com/search/"

class ThirdPartyProvider(MusicDataProvider):
    def __init__(self, api_key: str):
        self._api_key = api_key

    def fetch(self, track_id: str, title: str = "", artist: str = "", **kwargs) -> Optional[AudioFeatures]:
        if not self._api_key or not title:
            return None
        try:
            resp = requests.get(
                _SEARCH_URL,
                params={"api_key": self._api_key, "type": "both",
                        "lookup": f"song:{title}+artist:{artist}"},
                timeout=5,
            )
            data = resp.json().get("search", [])
            if not data:
                return None
            item = data[0]
            bpm = float(item.get("tempo", 0) or 0)
            if bpm == 0:
                return None
            return AudioFeatures(
                bpm=bpm, energy=0.5, valence=0.5,
                mood_tag="unknown", beat_grid=[], source_tier=2,
            )
        except Exception as e:
            logger.error("ThirdPartyProvider error track=%s err=%s", track_id, e)
            return None
