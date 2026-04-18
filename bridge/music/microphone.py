# bridge/music/microphone.py
import logging
from typing import Optional
import numpy as np
import sounddevice as sd
import librosa
from bridge.music.provider import MusicDataProvider
from bridge.music.types import AudioFeatures, BeatEvent

logger = logging.getLogger("lumiq")
_SAMPLE_RATE = 22050

class MicrophoneProvider(MusicDataProvider):
    def __init__(self, record_duration: int = 10):
        self._duration = record_duration

    def fetch(self, track_id: str, **kwargs) -> Optional[AudioFeatures]:
        try:
            logger.info("mic: recording %ds for beat detection", self._duration)
            audio = sd.rec(
                int(self._duration * _SAMPLE_RATE),
                samplerate=_SAMPLE_RATE, channels=1, dtype="float32"
            )
            sd.wait()
            audio = np.array(audio).flatten()
            tempo, beat_frames = librosa.beat.beat_track(y=audio, sr=_SAMPLE_RATE)
            beat_times = librosa.frames_to_time(beat_frames, sr=_SAMPLE_RATE)
            beat_grid = [
                BeatEvent(start=float(t), duration=60.0 / max(float(tempo), 1), confidence=0.5)
                for t in beat_times
            ]
            return AudioFeatures(
                bpm=float(tempo), energy=0.5, valence=0.5,
                mood_tag="mic_detected", beat_grid=beat_grid, source_tier=3,
            )
        except Exception as e:
            logger.error("MicrophoneProvider error: %s", e)
            return None
