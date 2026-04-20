from dataclasses import dataclass, field
from typing import List


@dataclass
class Device:
    id: str
    tuya_id: str
    local_key: str
    address: str
    type: str           # "color_bulb" | "tubelight"
    x: float
    y: float
    zone: str
    latency_ms: int
    online: bool
    capabilities: List[str]  # e.g. ["rgb", "brightness", "white"]
    version: str = "3.5"


@dataclass
class Command:
    device_id: str
    hex_color: str      # e.g. "#ff0000"
    brightness_pct: int # 0–100
    at_timestamp: float # unix epoch seconds
