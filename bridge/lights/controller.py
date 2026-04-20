import time
import logging
from typing import List, Dict
import tinytuya
from bridge.lights.types import Device, Command

logger = logging.getLogger("lumiq")


def _hex_to_rgb(hex_color: str):
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


class LightController:
    def __init__(self, devices: List[Device]):
        self._devices: Dict[str, Device] = {d.id: d for d in devices}
        self._bulbs: Dict[str, tinytuya.BulbDevice] = {}

    def _get_bulb(self, device_id: str) -> tinytuya.BulbDevice:
        if device_id not in self._bulbs:
            d = self._devices[device_id]
            bulb = tinytuya.BulbDevice(
                dev_id=d.tuya_id,
                address=d.address,
                local_key=d.local_key,
                version=str(getattr(d, 'version', '3.5')),
            )
            bulb.set_bulb_type("A")   # Wipro v3.5 uses DPS 20-27 (Type A)
            bulb.set_socketPersistent(True)
            self._bulbs[device_id] = bulb
        return self._bulbs[device_id]

    def send_command(self, cmd: Command):
        if cmd.device_id not in self._devices:
            logger.warning("send_command: unknown device %s", cmd.device_id)
            return
        try:
            bulb = self._get_bulb(cmd.device_id)
            r, g, b = _hex_to_rgb(cmd.hex_color)
            bulb.set_colour(r, g, b)
            bulb.set_brightness_percentage(cmd.brightness_pct)
            logger.info("cmd device=%s color=%s bright=%d",
                        cmd.device_id, cmd.hex_color, cmd.brightness_pct)
        except Exception as e:
            logger.error("send_command failed device=%s error=%s", cmd.device_id, e)
            # Drop the stale connection so the next attempt reconnects fresh
            self._bulbs.pop(cmd.device_id, None)

    def blink(self, device_id: str):
        bulb = self._get_bulb(device_id)
        bulb.turn_off()
        time.sleep(0.4)
        bulb.turn_on()

    def measure_latency(self, device_id: str) -> int:
        bulb = self._get_bulb(device_id)
        start = time.time()
        bulb.status()
        elapsed_ms = int((time.time() - start) * 1000)
        logger.info("latency device=%s ms=%d", device_id, elapsed_ms)
        return elapsed_ms

    def update_devices(self, devices: List[Device]):
        self._devices = {d.id: d for d in devices}
        self._bulbs = {}  # reset connections on room change
