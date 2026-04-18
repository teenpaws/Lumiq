# bridge/choreography/layer.py
import logging
import time
from typing import List
from bridge.choreography.registry import filter_eligible
from bridge.choreography.patterns import compute_commands
from bridge.choreography.scheduler import BeatScheduler
from bridge.lights.types import Device, Command
from bridge.music.types import AudioFeatures

logger = logging.getLogger("lumiq")

class ChoreographyLayer:
    def __init__(self, send_fn):
        self._scheduler = BeatScheduler(send_fn=send_fn)
        self._devices: List[Device] = []

    def update_devices(self, devices: List[Device]):
        self._devices = devices

    def play_with_position(self, audio_features: AudioFeatures, profile: dict, position_s: float):
        """Schedule commands for all upcoming beats given current playback position (seconds)."""
        self._scheduler.clear()
        eligible = filter_eligible(self._devices, profile.get("pattern_preferences", ["pulse_all"]))
        if not eligible:
            eligible = ["pulse_all"]
        active_pattern = eligible[0]
        now = time.time()

        commands: List[Command] = []
        for beat in audio_features.beat_grid:
            beat_wall_clock = now + (beat.start - position_s)
            if beat_wall_clock < now - 0.1:
                continue  # beat already passed
            if beat_wall_clock > now + 30:
                break  # only schedule 30s ahead
            cmds = compute_commands(active_pattern, self._devices, beat_wall_clock, profile)
            commands.extend(cmds)

        self._scheduler.schedule(commands)
        logger.info("choreography pattern=%s beats_scheduled=%d devices=%d",
                    active_pattern, len(audio_features.beat_grid), len(self._devices))

    def stop(self):
        self._scheduler.clear()
