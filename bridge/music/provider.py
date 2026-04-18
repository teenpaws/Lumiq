# bridge/music/provider.py
from abc import ABC, abstractmethod
from typing import Optional
from bridge.music.types import AudioFeatures

class MusicDataProvider(ABC):
    @abstractmethod
    def fetch(self, track_id: str, **kwargs) -> Optional[AudioFeatures]:
        """Return AudioFeatures or None if this provider cannot serve the track."""
        ...

def chain(providers, track_id: str, **kwargs) -> Optional[AudioFeatures]:
    """Try each provider in order; return first non-None result."""
    for provider in providers:
        try:
            result = provider.fetch(track_id, **kwargs)
            if result is not None:
                return result
        except Exception:
            continue
    return None
