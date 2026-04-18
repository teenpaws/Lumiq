# bridge/music/spotify.py
import logging
from typing import Optional
import requests
from bridge.music.provider import MusicDataProvider
from bridge.music.types import AudioFeatures, BeatEvent

logger = logging.getLogger("lumiq")

_FEATURES_URL = "https://api.spotify.com/v1/audio-features/{id}"
_ANALYSIS_URL = "https://api.spotify.com/v1/audio-analysis/{id}"

def _classify_mood(energy: float, valence: float) -> str:
    if energy > 0.7 and valence > 0.5:
        return "high_energy_positive"
    if energy > 0.7 and valence <= 0.5:
        return "high_energy_dark"
    if energy <= 0.4 and valence > 0.5:
        return "calm_warm"
    return "calm_nocturnal"

class SpotifyProvider(MusicDataProvider):
    def fetch(self, track_id: str, access_token: str = "", **kwargs) -> Optional[AudioFeatures]:
        headers = {"Authorization": f"Bearer {access_token}"}
        try:
            feat_resp = requests.get(
                _FEATURES_URL.format(id=track_id), headers=headers, timeout=5
            )
            if feat_resp.status_code != 200:
                logger.warning("Spotify features status=%d track=%s",
                               feat_resp.status_code, track_id)
                return None
            feat = feat_resp.json()

            anal_resp = requests.get(
                _ANALYSIS_URL.format(id=track_id), headers=headers, timeout=10
            )
            beats = []
            if anal_resp.status_code == 200:
                beats = [
                    BeatEvent(start=b["start"], duration=b["duration"],
                              confidence=b["confidence"])
                    for b in anal_resp.json().get("beats", [])
                ]

            return AudioFeatures(
                bpm=feat["tempo"],
                energy=feat["energy"],
                valence=feat["valence"],
                mood_tag=_classify_mood(feat["energy"], feat["valence"]),
                beat_grid=beats,
                source_tier=1,
            )
        except Exception as e:
            logger.error("SpotifyProvider error track=%s err=%s", track_id, e)
            return None
