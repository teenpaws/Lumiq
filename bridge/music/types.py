from dataclasses import dataclass, field
from typing import List


@dataclass
class BeatEvent:
    start: float       # seconds from track start
    duration: float
    confidence: float


@dataclass
class AudioFeatures:
    bpm: float
    energy: float      # 0.0–1.0
    valence: float     # 0.0–1.0  (musical positiveness)
    mood_tag: str      # e.g. "energetic", "calm_nocturnal"
    beat_grid: List[BeatEvent]
    source_tier: int   # 1=Spotify, 2=third-party, 3=mic
