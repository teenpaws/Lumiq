# Lumiq Bridge — Implementation Plan (Plan 1 of 2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Python Flask bridge that powers all Lumiq lighting logic — music data, profile caching, Claude-powered profile generation, choreography, and TinyTuya light control — testable end-to-end with curl before any PWA exists.

**Architecture:** Single Flask process with modular internal packages. Track changes arrive via `POST /track` from the PWA → `MusicDataProvider` chain fetches audio features → `ClaudeClient` generates/caches a lighting profile → `ChoreographyLayer` schedules latency-compensated per-bulb commands → `LightController` executes via TinyTuya over LAN. One background scheduler thread handles beat-accurate timing.

**Tech Stack:** Python 3.11, Flask 3.x, TinyTuya 1.x, `anthropic` SDK (Haiku 4.5 with prompt caching), `requests`, `librosa`, `sounddevice`, `python-dotenv`, `pydantic` v2, `pytest`, `pytest-mock`

---

## File Map

```
bridge/
  app.py                        # Flask create_app() factory, blueprint registration
  config.py                     # Config dataclass, load from .env
  logger.py                     # setup_logger() → RotatingFileHandler
  state.py                      # AppState singleton (current mode, active track, active profile)
  patterns.json                 # Shipped pattern registry (5 patterns)
  routes/
    __init__.py
    health.py                   # GET /health
    mode.py                     # GET/POST /mode
    room.py                     # GET/POST /room, POST /room/blink/<id>, POST /room/calibrate
    track.py                    # POST /track  (the main hot path)
    theme.py                    # POST /theme
    cron.py                     # POST /cron/run-now → 501
  music/
    __init__.py
    types.py                    # AudioFeatures dataclass
    provider.py                 # MusicDataProvider ABC + chain() orchestrator
    spotify.py                  # SpotifyProvider (tier 1)
    third_party.py              # ThirdPartyProvider / GetSongBPM (tier 2)
    microphone.py               # MicrophoneProvider / librosa (tier 3)
  profiles/
    __init__.py
    types.py                    # Profile TypedDict, validate_profile()
    cache.py                    # ProfileCache class (filesystem JSON)
    presets.py                  # load_preset(name) helper
  claude_client.py              # ClaudeClient — generate_auto_profile(), generate_theme_profile()
  choreography/
    __init__.py
    registry.py                 # load_registry(), filter_eligible(devices, pattern_prefs)
    patterns.py                 # compute_commands(pattern, devices, beat_time, profile) → List[Command]
    scheduler.py                # BeatScheduler — heapq background thread
    layer.py                    # ChoreographyLayer — ties registry + patterns + scheduler together
  lights/
    __init__.py
    types.py                    # Device, Command dataclasses
    controller.py               # LightController — TinyTuya wrapper
    room.py                     # RoomStore — room_profile.json read/write
tests/
  conftest.py                   # Shared fixtures (sample room, profile, beat_grid)
  test_profile_cache.py
  test_music_provider.py
  test_choreography_patterns.py
  test_choreography_scheduler.py
  test_lights_controller.py
  test_integration_critical_path.py
profiles/
  presets/
    club.json
    lounge.json
    party.json
    chill.json
    concert.json
  themes/                       # Empty; populated at runtime
  tracks/                       # Empty; populated at runtime
.env.example
requirements.txt
pytest.ini
README.md
```

---

## Task 1: Project scaffold

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `pytest.ini`
- Create: all `__init__.py` stubs + empty directory tree

- [ ] **Step 1: Create the directory tree**

```bash
cd "E:/Claude Projects/Lumiq"
mkdir -p bridge/routes bridge/music bridge/profiles bridge/choreography bridge/lights
mkdir -p tests profiles/presets profiles/themes profiles/tracks logs
touch bridge/__init__.py bridge/routes/__init__.py bridge/music/__init__.py
touch bridge/profiles/__init__.py bridge/choreography/__init__.py bridge/lights/__init__.py
touch tests/__init__.py tests/conftest.py
```

- [ ] **Step 2: Initialize git**

```bash
cd "E:/Claude Projects/Lumiq"
git init
```

- [ ] **Step 3: Create `requirements.txt`**

```text
anthropic>=0.40.0
flask>=3.0.0
tinytuya>=1.15.0
requests>=2.32.0
python-dotenv>=1.0.0
pydantic>=2.0.0
librosa>=0.10.0
sounddevice>=0.4.0
numpy>=1.26.0
pytest>=8.0.0
pytest-mock>=3.14.0
requests-mock>=1.12.0
```

- [ ] **Step 4: Create `.env.example`**

```dotenv
# Claude API key (required for Auto and Theme modes)
CLAUDE_API_KEY=sk-ant-...

# Spotify (tier 1 music data — requires pre-Nov-2024 developer app)
# Set USE_SPOTIFY_FEATURES=false to skip tier 1 and start from tier 2
USE_SPOTIFY_FEATURES=true

# Third-party music data — GetSongBPM (tier 2)
# Get a free key at https://getsongbpm.com/api
GETSONGBPM_API_KEY=...

# Bridge network config
BRIDGE_PORT=5000
PROFILES_DIR=profiles
ROOM_PROFILE_PATH=room_profile.json
LOG_PATH=logs/bridge.log
```

- [ ] **Step 5: Create `pytest.ini`**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
```

- [ ] **Step 6: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: All packages install without errors.

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "chore: project scaffold, requirements, env template"
```

---

## Task 2: Config + Logger

**Files:**
- Create: `bridge/config.py`
- Create: `bridge/logger.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_config.py
import os
from bridge.config import Config

def test_config_reads_env(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    monkeypatch.setenv("BRIDGE_PORT", "6000")
    monkeypatch.setenv("USE_SPOTIFY_FEATURES", "false")
    cfg = Config.from_env()
    assert cfg.claude_api_key == "test-key"
    assert cfg.bridge_port == 6000
    assert cfg.use_spotify_features is False

def test_config_defaults(monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "x")
    cfg = Config.from_env()
    assert cfg.bridge_port == 5000
    assert cfg.use_spotify_features is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.config'`

- [ ] **Step 3: Create `bridge/config.py`**

```python
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    claude_api_key: str
    bridge_port: int
    profiles_dir: str
    room_profile_path: str
    log_path: str
    use_spotify_features: bool
    getsongbpm_api_key: str

    @classmethod
    def from_env(cls) -> "Config":
        return cls(
            claude_api_key=os.environ["CLAUDE_API_KEY"],
            bridge_port=int(os.getenv("BRIDGE_PORT", "5000")),
            profiles_dir=os.getenv("PROFILES_DIR", "profiles"),
            room_profile_path=os.getenv("ROOM_PROFILE_PATH", "room_profile.json"),
            log_path=os.getenv("LOG_PATH", "logs/bridge.log"),
            use_spotify_features=os.getenv("USE_SPOTIFY_FEATURES", "true").lower() == "true",
            getsongbpm_api_key=os.getenv("GETSONGBPM_API_KEY", ""),
        )
```

- [ ] **Step 4: Create `bridge/logger.py`**

```python
import logging
import os
from logging.handlers import RotatingFileHandler

def setup_logger(log_path: str) -> logging.Logger:
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logger = logging.getLogger("lumiq")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = RotatingFileHandler(log_path, maxBytes=10 * 1024 * 1024, backupCount=5)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        ))
        logger.addHandler(handler)
        logger.addHandler(logging.StreamHandler())  # also log to stdout during dev
    return logger
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_config.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add bridge/config.py bridge/logger.py tests/test_config.py
git commit -m "feat: Config dataclass and rotating logger"
```

---

## Task 3: Shared type definitions

**Files:**
- Create: `bridge/lights/types.py`
- Create: `bridge/music/types.py`
- Create: `bridge/profiles/types.py`

- [ ] **Step 1: Create `bridge/lights/types.py`**

```python
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

@dataclass
class Command:
    device_id: str
    hex_color: str      # e.g. "#ff0000"
    brightness_pct: int # 0–100
    at_timestamp: float # unix epoch seconds
```

- [ ] **Step 2: Create `bridge/music/types.py`**

```python
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
```

- [ ] **Step 3: Create `bridge/profiles/types.py`**

```python
from typing import List, Literal

BEAT_RESPONSES = {"breathe", "pulse", "sweep", "strobe", "none"}
SOURCES = {"preset", "theme", "auto_track"}

def validate_profile(p: dict) -> dict:
    required = {"profile_name", "source", "base_colors", "transition_speed_ms",
                "beat_response", "energy_multiplier", "mood_tag",
                "pattern_preferences", "composition_rule"}
    missing = required - p.keys()
    if missing:
        raise ValueError(f"Profile missing fields: {missing}")
    if p["beat_response"] not in BEAT_RESPONSES:
        raise ValueError(f"Invalid beat_response: {p['beat_response']}")
    if p["source"] not in SOURCES:
        raise ValueError(f"Invalid source: {p['source']}")
    return p
```

- [ ] **Step 4: Write + run quick smoke tests**

```python
# tests/test_types.py
from bridge.lights.types import Device, Command
from bridge.music.types import AudioFeatures, BeatEvent
from bridge.profiles.types import validate_profile

def test_device_fields():
    d = Device(id="b1", tuya_id="abc", local_key="xyz", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    assert d.latency_ms == 40

def test_validate_profile_missing_field():
    import pytest
    with pytest.raises(ValueError, match="missing fields"):
        validate_profile({"profile_name": "x"})

def test_validate_profile_ok():
    p = {
        "profile_name": "test", "source": "preset", "base_colors": ["#ff0000"],
        "transition_speed_ms": 500, "beat_response": "pulse", "energy_multiplier": 0.8,
        "mood_tag": "energetic", "pattern_preferences": ["pulse_all"],
        "composition_rule": "last_write_wins"
    }
    assert validate_profile(p) == p
```

```bash
pytest tests/test_types.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/lights/types.py bridge/music/types.py bridge/profiles/types.py tests/test_types.py
git commit -m "feat: shared type definitions — Device, Command, AudioFeatures, Profile"
```

---

## Task 4: Room Profile Store

**Files:**
- Create: `bridge/lights/room.py`
- Test: `tests/test_room_store.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_room_store.py
import json, os, pytest
from bridge.lights.room import RoomStore
from bridge.lights.types import Device

@pytest.fixture
def store(tmp_path):
    path = str(tmp_path / "room_profile.json")
    return RoomStore(path)

def test_empty_store_returns_no_devices(store):
    assert store.get_devices() == []

def test_save_and_reload(store, tmp_path):
    devices = [
        Device(id="b1", tuya_id="t1", local_key="k1", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    ]
    floor_plan = {"width_m": 4.2, "length_m": 3.6, "shape": "rectangle"}
    store.save(floor_plan, devices)

    store2 = RoomStore(str(tmp_path / "room_profile.json"))
    loaded = store2.get_devices()
    assert len(loaded) == 1
    assert loaded[0].id == "b1"
    assert loaded[0].latency_ms == 40

def test_update_device_latency(store):
    devices = [
        Device(id="b1", tuya_id="t1", local_key="k1", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    ]
    store.save({"width_m": 4.0, "length_m": 3.0, "shape": "rectangle"}, devices)
    store.update_device(id="b1", latency_ms=65)
    assert store.get_device("b1").latency_ms == 65

def test_mark_device_offline(store):
    devices = [
        Device(id="b1", tuya_id="t1", local_key="k1", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    ]
    store.save({"width_m": 4.0, "length_m": 3.0, "shape": "rectangle"}, devices)
    store.update_device(id="b1", online=False)
    assert store.get_device("b1").online is False
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_room_store.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.lights.room'`

- [ ] **Step 3: Create `bridge/lights/room.py`**

```python
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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_room_store.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/lights/room.py tests/test_room_store.py
git commit -m "feat: RoomStore — persist and query room_profile.json"
```

---

## Task 5: Light Controller

**Files:**
- Create: `bridge/lights/controller.py`
- Test: `tests/test_lights_controller.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_lights_controller.py
import pytest
from unittest.mock import MagicMock, patch
from bridge.lights.controller import LightController
from bridge.lights.types import Device, Command
import time

@pytest.fixture
def device():
    return Device(id="b1", tuya_id="tid1", local_key="lk1", address="192.168.1.10",
                  type="color_bulb", x=1.0, y=0.5, zone="fl",
                  latency_ms=40, online=True, capabilities=["rgb"])

def test_send_command_calls_tuya(device, mocker):
    mock_bulb = MagicMock()
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)
    ctrl = LightController([device])
    cmd = Command(device_id="b1", hex_color="#ff0000", brightness_pct=80,
                  at_timestamp=time.time())
    ctrl.send_command(cmd)
    mock_bulb.set_colour.assert_called_once_with(255, 0, 0)
    mock_bulb.set_brightness_percentage.assert_called_once_with(80)

def test_send_command_unknown_device_logs_and_skips(device, mocker, caplog):
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=MagicMock())
    ctrl = LightController([device])
    cmd = Command(device_id="unknown", hex_color="#ffffff", brightness_pct=100,
                  at_timestamp=time.time())
    ctrl.send_command(cmd)  # should not raise

def test_blink_sends_two_commands(device, mocker):
    mock_bulb = MagicMock()
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)
    mocker.patch("bridge.lights.controller.time.sleep")
    ctrl = LightController([device])
    ctrl.blink("b1")
    assert mock_bulb.turn_off.call_count == 1
    assert mock_bulb.turn_on.call_count == 1

def test_measure_latency_returns_ms(device, mocker):
    mock_bulb = MagicMock()
    mock_bulb.status.return_value = {"dps": {"20": True}}
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)
    ctrl = LightController([device])
    latency = ctrl.measure_latency("b1")
    assert isinstance(latency, int)
    assert 0 <= latency <= 5000
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_lights_controller.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.lights.controller'`

- [ ] **Step 3: Create `bridge/lights/controller.py`**

```python
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
                version="3.3",
            )
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
            logger.info("cmd device=%s color=%s bright=%d latency_target_ms=%s",
                        cmd.device_id, cmd.hex_color, cmd.brightness_pct,
                        self._devices[cmd.device_id].latency_ms)
        except Exception as e:
            logger.error("send_command failed device=%s error=%s", cmd.device_id, e)
            self._devices[cmd.device_id].online = False

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
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_lights_controller.py -v
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/lights/controller.py tests/test_lights_controller.py
git commit -m "feat: LightController — TinyTuya wrapper with blink and latency measurement"
```

---

## Task 6: Profile Cache

**Files:**
- Create: `bridge/profiles/cache.py`
- Test: `tests/test_profile_cache.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_profile_cache.py
import pytest
from bridge.profiles.cache import ProfileCache

SAMPLE_PROFILE = {
    "profile_name": "club", "source": "preset", "base_colors": ["#ff0000"],
    "transition_speed_ms": 200, "beat_response": "strobe", "energy_multiplier": 1.0,
    "mood_tag": "high_energy", "pattern_preferences": ["pulse_all"],
    "composition_rule": "last_write_wins", "created_at": "2026-04-18T00:00:00Z"
}

@pytest.fixture
def cache(tmp_path):
    return ProfileCache(str(tmp_path))

def test_miss_returns_none(cache):
    assert cache.get("tracks", "nonexistent") is None

def test_put_and_get(cache):
    cache.put("themes", "tokyo_rain", SAMPLE_PROFILE)
    loaded = cache.get("themes", "tokyo_rain")
    assert loaded["profile_name"] == "club"

def test_list_empty(cache):
    assert cache.list("tracks") == []

def test_list_after_put(cache):
    cache.put("tracks", "track_abc", SAMPLE_PROFILE)
    cache.put("tracks", "track_def", SAMPLE_PROFILE)
    names = cache.list("tracks")
    assert sorted(names) == ["track_abc", "track_def"]

def test_put_validates_profile(cache):
    import pytest
    with pytest.raises(ValueError):
        cache.put("tracks", "bad", {"profile_name": "incomplete"})
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_profile_cache.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.profiles.cache'`

- [ ] **Step 3: Create `bridge/profiles/cache.py`**

```python
import json
import os
from typing import Optional, List
from bridge.profiles.types import validate_profile

class ProfileCache:
    def __init__(self, base_dir: str):
        self._base = base_dir
        for sub in ("presets", "themes", "tracks"):
            os.makedirs(os.path.join(base_dir, sub), exist_ok=True)

    def _path(self, source: str, name: str) -> str:
        return os.path.join(self._base, source, f"{name}.json")

    def get(self, source: str, name: str) -> Optional[dict]:
        p = self._path(source, name)
        if not os.path.exists(p):
            return None
        with open(p) as f:
            return json.load(f)

    def put(self, source: str, name: str, profile: dict):
        validate_profile(profile)
        with open(self._path(source, name), "w") as f:
            json.dump(profile, f, indent=2)

    def list(self, source: str) -> List[str]:
        d = os.path.join(self._base, source)
        return [f[:-5] for f in os.listdir(d) if f.endswith(".json")]
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_profile_cache.py -v
```

Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/profiles/cache.py tests/test_profile_cache.py
git commit -m "feat: ProfileCache — filesystem JSON store for presets/themes/tracks"
```

---

## Task 7: Pattern Registry + Eligibility

**Files:**
- Create: `bridge/patterns.json`
- Create: `bridge/choreography/registry.py`
- Test: `tests/test_choreography_registry.py`

- [ ] **Step 1: Create `bridge/patterns.json`**

```json
[
  {
    "name": "pulse_all",
    "min_bulbs": 1,
    "requires": [],
    "composable_with": []
  },
  {
    "name": "breathe_all",
    "min_bulbs": 1,
    "requires": [],
    "composable_with": ["wave_lr", "alternate_zones"]
  },
  {
    "name": "alternate_zones",
    "min_bulbs": 2,
    "requires": ["zones"],
    "composable_with": ["breathe_all"]
  },
  {
    "name": "wave_lr",
    "min_bulbs": 3,
    "requires": ["x_coords"],
    "composable_with": ["breathe_all"]
  },
  {
    "name": "radial",
    "min_bulbs": 4,
    "requires": ["x_coords", "y_coords"],
    "composable_with": []
  }
]
```

- [ ] **Step 2: Write failing tests**

```python
# tests/test_choreography_registry.py
from bridge.choreography.registry import load_registry, filter_eligible
from bridge.lights.types import Device

def make_device(id, x, y, zone, n=1):
    return Device(id=id, tuya_id=id, local_key="k", address="192.168.1.1",
                  type="color_bulb", x=x, y=y, zone=zone,
                  latency_ms=40, online=True, capabilities=["rgb"])

def test_load_registry_returns_five_patterns():
    patterns = load_registry()
    assert len(patterns) == 5
    names = {p["name"] for p in patterns}
    assert "wave_lr" in names

def test_single_bulb_only_pulse_and_breathe():
    devices = [make_device("b1", 1.0, 1.0, "center")]
    eligible = filter_eligible(devices, ["wave_lr", "pulse_all", "breathe_all"])
    assert set(eligible) == {"pulse_all", "breathe_all"}

def test_three_bulbs_enables_wave_lr():
    devices = [make_device(f"b{i}", float(i), 1.0, "z") for i in range(3)]
    eligible = filter_eligible(devices, ["wave_lr", "pulse_all"])
    assert "wave_lr" in eligible

def test_four_bulbs_enables_radial():
    devices = [make_device(f"b{i}", float(i % 2), float(i // 2), "z") for i in range(4)]
    eligible = filter_eligible(devices, ["radial", "pulse_all"])
    assert "radial" in eligible

def test_offline_bulbs_not_counted():
    devices = [make_device(f"b{i}", float(i), 1.0, "z") for i in range(3)]
    devices[2].online = False  # only 2 online
    eligible = filter_eligible(devices, ["wave_lr", "pulse_all"])
    assert "wave_lr" not in eligible

def test_preferences_order_preserved():
    devices = [make_device(f"b{i}", float(i), 1.0, "z") for i in range(4)]
    prefs = ["radial", "wave_lr", "pulse_all"]
    eligible = filter_eligible(devices, prefs)
    assert eligible.index("radial") < eligible.index("pulse_all")
```

- [ ] **Step 3: Run to verify failure**

```bash
pytest tests/test_choreography_registry.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.choreography.registry'`

- [ ] **Step 4: Create `bridge/choreography/registry.py`**

```python
import json
import os
from typing import List
from bridge.lights.types import Device

_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "..", "patterns.json")

def load_registry() -> List[dict]:
    with open(os.path.normpath(_REGISTRY_PATH)) as f:
        return json.load(f)

def filter_eligible(devices: List[Device], pattern_preferences: List[str]) -> List[str]:
    online_devices = [d for d in devices if d.online]
    registry = {p["name"]: p for p in load_registry()}
    eligible = []
    for pref in pattern_preferences:
        if pref not in registry:
            continue
        pattern = registry[pref]
        if len(online_devices) < pattern["min_bulbs"]:
            continue
        reqs_met = True
        for req in pattern["requires"]:
            if req == "x_coords" and not all(hasattr(d, "x") for d in online_devices):
                reqs_met = False
            if req == "y_coords" and not all(hasattr(d, "y") for d in online_devices):
                reqs_met = False
            if req == "zones" and not all(d.zone for d in online_devices):
                reqs_met = False
        if reqs_met:
            eligible.append(pref)
    return eligible
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_choreography_registry.py -v
```

Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
git add bridge/patterns.json bridge/choreography/registry.py tests/test_choreography_registry.py
git commit -m "feat: pattern registry with eligibility filtering based on room devices"
```

---

## Task 8: Choreography Pattern Math

**Files:**
- Create: `bridge/choreography/patterns.py`
- Test: `tests/test_choreography_patterns.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_choreography_patterns.py
import pytest
from bridge.choreography.patterns import compute_commands
from bridge.lights.types import Device, Command

def make_device(id, x, y, zone, latency_ms=40):
    return Device(id=id, tuya_id=id, local_key="k", address="192.168.1.1",
                  type="color_bulb", x=x, y=y, zone=zone,
                  latency_ms=latency_ms, online=True, capabilities=["rgb"])

PROFILE = {
    "base_colors": ["#ff0000", "#0000ff", "#00ff00"],
    "beat_response": "pulse",
    "energy_multiplier": 0.8,
    "transition_speed_ms": 400,
}
BEAT_TIME = 100.0  # unix timestamp

def test_pulse_all_fires_all_devices_simultaneously():
    devices = [make_device("b1", 0.0, 0.0, "fl"), make_device("b2", 1.0, 0.0, "fr")]
    cmds = compute_commands("pulse_all", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 2
    # all at same beat time (minus latency)
    times = {c.at_timestamp for c in cmds}
    # different latency per device so times differ
    assert cmds[0].hex_color == cmds[1].hex_color

def test_pulse_all_applies_latency_compensation():
    d1 = make_device("b1", 0.0, 0.0, "fl", latency_ms=40)
    d2 = make_device("b2", 1.0, 0.0, "fr", latency_ms=80)
    cmds = compute_commands("pulse_all", [d1, d2], BEAT_TIME, PROFILE)
    cmd1 = next(c for c in cmds if c.device_id == "b1")
    cmd2 = next(c for c in cmds if c.device_id == "b2")
    # b2 command should be scheduled earlier to compensate for higher latency
    assert cmd2.at_timestamp < cmd1.at_timestamp

def test_wave_lr_staggers_by_x_position():
    devices = [
        make_device("b1", 0.0, 0.0, "fl"),  # leftmost
        make_device("b2", 1.0, 0.0, "fm"),  # middle
        make_device("b3", 2.0, 0.0, "fr"),  # rightmost
    ]
    cmds = compute_commands("wave_lr", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 3
    by_device = {c.device_id: c.at_timestamp for c in cmds}
    # b1 fires first (leftmost), b3 fires last (rightmost)
    assert by_device["b1"] <= by_device["b2"] <= by_device["b3"]

def test_breathe_all_returns_all_devices():
    devices = [make_device(f"b{i}", float(i), 0.0, "z") for i in range(4)]
    cmds = compute_commands("breathe_all", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 4

def test_alternate_zones_splits_by_zone():
    devices = [
        make_device("b1", 0.0, 0.0, "front"),
        make_device("b2", 1.0, 0.0, "front"),
        make_device("b3", 0.0, 1.0, "back"),
        make_device("b4", 1.0, 1.0, "back"),
    ]
    cmds = compute_commands("alternate_zones", devices, BEAT_TIME, PROFILE)
    assert len(cmds) == 4
    # on beat: one zone is bright, other is dim
    bright_cmds = [c for c in cmds if c.brightness_pct > 50]
    dim_cmds = [c for c in cmds if c.brightness_pct <= 50]
    assert len(bright_cmds) == 2
    assert len(dim_cmds) == 2
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_choreography_patterns.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.choreography.patterns'`

- [ ] **Step 3: Create `bridge/choreography/patterns.py`**

```python
import math
import time
from typing import List
from bridge.lights.types import Device, Command

_BUFFER_S = 0.05  # 50ms pre-send buffer

def _compensation(device: Device, beat_time: float) -> float:
    """Return scheduled wall-clock time: beat_time - latency - buffer."""
    return beat_time - (device.latency_ms / 1000.0) - _BUFFER_S

def _pick_color(profile: dict, index: int = 0) -> str:
    colors = profile.get("base_colors", ["#ffffff"])
    return colors[index % len(colors)]

def compute_commands(
    pattern: str,
    devices: List[Device],
    beat_time: float,
    profile: dict,
) -> List[Command]:
    online = [d for d in devices if d.online]
    if pattern == "pulse_all":
        return _pulse_all(online, beat_time, profile)
    if pattern == "breathe_all":
        return _breathe_all(online, beat_time, profile)
    if pattern == "wave_lr":
        return _wave_lr(online, beat_time, profile)
    if pattern == "alternate_zones":
        return _alternate_zones(online, beat_time, profile)
    if pattern == "radial":
        return _radial(online, beat_time, profile)
    return []

def _pulse_all(devices, beat_time, profile):
    color = _pick_color(profile)
    brightness = int(100 * profile.get("energy_multiplier", 0.8))
    return [Command(
        device_id=d.id,
        hex_color=color,
        brightness_pct=brightness,
        at_timestamp=_compensation(d, beat_time),
    ) for d in devices]

def _breathe_all(devices, beat_time, profile):
    # Slow sinusoidal brightness at beat — gentle swell
    brightness = int(60 * profile.get("energy_multiplier", 0.6))
    color = _pick_color(profile, 1)
    return [Command(
        device_id=d.id,
        hex_color=color,
        brightness_pct=brightness,
        at_timestamp=_compensation(d, beat_time),
    ) for d in devices]

def _wave_lr(devices, beat_time, profile):
    sorted_devices = sorted(devices, key=lambda d: d.x)
    n = len(sorted_devices)
    # Spread wave across beat duration (assume 500ms default)
    beat_duration = profile.get("transition_speed_ms", 500) / 1000.0
    cmds = []
    for i, d in enumerate(sorted_devices):
        stagger = (i / max(n - 1, 1)) * beat_duration
        color = _pick_color(profile, i)
        brightness = int(100 * profile.get("energy_multiplier", 0.8))
        cmds.append(Command(
            device_id=d.id,
            hex_color=color,
            brightness_pct=brightness,
            at_timestamp=_compensation(d, beat_time) + stagger,
        ))
    return cmds

def _alternate_zones(devices, beat_time, profile):
    zones = sorted({d.zone for d in devices})
    cmds = []
    # Even-indexed zones bright, odd-indexed zones dim (alternates each beat)
    current_time = time.time()
    beat_index = int(beat_time) % 2  # alternates 0/1 per beat
    for d in devices:
        zone_index = zones.index(d.zone)
        is_active = (zone_index % 2) == beat_index
        brightness = int(90 * profile.get("energy_multiplier", 0.8)) if is_active else 15
        color = _pick_color(profile, zone_index)
        cmds.append(Command(
            device_id=d.id,
            hex_color=color,
            brightness_pct=brightness,
            at_timestamp=_compensation(d, beat_time),
        ))
    return cmds

def _radial(devices, beat_time, profile):
    cx = sum(d.x for d in devices) / len(devices)
    cy = sum(d.y for d in devices) / len(devices)
    max_dist = max(math.sqrt((d.x - cx) ** 2 + (d.y - cy) ** 2) for d in devices) or 1.0
    beat_duration = profile.get("transition_speed_ms", 500) / 1000.0
    cmds = []
    for d in devices:
        dist = math.sqrt((d.x - cx) ** 2 + (d.y - cy) ** 2)
        stagger = (dist / max_dist) * beat_duration
        brightness = int(100 * profile.get("energy_multiplier", 0.8))
        cmds.append(Command(
            device_id=d.id,
            hex_color=_pick_color(profile),
            brightness_pct=brightness,
            at_timestamp=_compensation(d, beat_time) + stagger,
        ))
    return cmds
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_choreography_patterns.py -v
```

Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/choreography/patterns.py tests/test_choreography_patterns.py
git commit -m "feat: choreography pattern math — pulse, breathe, wave_lr, alternate_zones, radial"
```

---

## Task 9: Beat Scheduler

**Files:**
- Create: `bridge/choreography/scheduler.py`
- Test: `tests/test_choreography_scheduler.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_choreography_scheduler.py
import time
import threading
from bridge.choreography.scheduler import BeatScheduler
from bridge.lights.types import Command

def test_scheduler_executes_due_commands():
    executed = []
    def fake_send(cmd):
        executed.append(cmd)

    scheduler = BeatScheduler(send_fn=fake_send)
    now = time.time()
    cmds = [
        Command(device_id="b1", hex_color="#ff0000", brightness_pct=80,
                at_timestamp=now + 0.05),
        Command(device_id="b2", hex_color="#0000ff", brightness_pct=60,
                at_timestamp=now + 0.10),
    ]
    scheduler.schedule(cmds)
    time.sleep(0.25)
    scheduler.stop()
    assert len(executed) == 2

def test_scheduler_executes_in_time_order():
    order = []
    def fake_send(cmd):
        order.append(cmd.device_id)

    scheduler = BeatScheduler(send_fn=fake_send)
    now = time.time()
    cmds = [
        Command(device_id="second", hex_color="#ffffff", brightness_pct=50,
                at_timestamp=now + 0.12),
        Command(device_id="first", hex_color="#ffffff", brightness_pct=50,
                at_timestamp=now + 0.05),
    ]
    scheduler.schedule(cmds)
    time.sleep(0.25)
    scheduler.stop()
    assert order == ["first", "second"]

def test_clear_removes_pending_commands():
    executed = []
    def fake_send(cmd):
        executed.append(cmd)

    scheduler = BeatScheduler(send_fn=fake_send)
    now = time.time()
    cmds = [Command(device_id="b1", hex_color="#ff0000", brightness_pct=80,
                    at_timestamp=now + 1.0)]  # 1 second in future
    scheduler.schedule(cmds)
    scheduler.clear()
    time.sleep(0.1)
    scheduler.stop()
    assert executed == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_choreography_scheduler.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.choreography.scheduler'`

- [ ] **Step 3: Create `bridge/choreography/scheduler.py`**

```python
import heapq
import threading
import time
import logging
from typing import Callable, List
from bridge.lights.types import Command

logger = logging.getLogger("lumiq")

class BeatScheduler:
    def __init__(self, send_fn: Callable[[Command], None]):
        self._queue: list = []  # heapq of (at_timestamp, Command)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._send_fn = send_fn
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def schedule(self, commands: List[Command]):
        with self._lock:
            for cmd in commands:
                heapq.heappush(self._queue, (cmd.at_timestamp, id(cmd), cmd))

    def clear(self):
        with self._lock:
            self._queue.clear()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=1.0)

    def _run(self):
        while not self._stop_event.is_set():
            now = time.time()
            with self._lock:
                while self._queue and self._queue[0][0] <= now:
                    _, _, cmd = heapq.heappop(self._queue)
                    try:
                        self._send_fn(cmd)
                    except Exception as e:
                        logger.error("scheduler send error device=%s err=%s", cmd.device_id, e)
            time.sleep(0.005)  # 5ms tick
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_choreography_scheduler.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/choreography/scheduler.py tests/test_choreography_scheduler.py
git commit -m "feat: BeatScheduler — heapq priority queue with 5ms tick for beat-accurate lighting"
```

---

## Task 10: Choreography Layer

**Files:**
- Create: `bridge/choreography/layer.py`
- Test: (inline in integration test — Task 16)

- [ ] **Step 1: Create `bridge/choreography/layer.py`**

```python
import logging
import time
from typing import List, Optional
from bridge.choreography.registry import filter_eligible
from bridge.choreography.patterns import compute_commands
from bridge.choreography.scheduler import BeatScheduler
from bridge.lights.types import Device, Command
from bridge.music.types import BeatEvent, AudioFeatures

logger = logging.getLogger("lumiq")

class ChoreographyLayer:
    def __init__(self, send_fn):
        self._scheduler = BeatScheduler(send_fn=send_fn)
        self._devices: List[Device] = []

    def update_devices(self, devices: List[Device]):
        self._devices = devices

    def play(self, audio_features: AudioFeatures, profile: dict):
        """Schedule commands for all upcoming beats in the beat grid."""
        self._scheduler.clear()
        eligible = filter_eligible(self._devices, profile.get("pattern_preferences", ["pulse_all"]))
        if not eligible:
            eligible = ["pulse_all"]
        active_pattern = eligible[0]
        now = time.time()
        position_s = 0.0  # caller should pass this; defaulting to 0 for now

        commands: List[Command] = []
        for beat in audio_features.beat_grid:
            beat_wall_clock = now + (beat.start - position_s)
            if beat_wall_clock < now:
                continue  # already passed
            if beat_wall_clock > now + 30:
                break  # only schedule 30s ahead
            cmds = compute_commands(active_pattern, self._devices, beat_wall_clock, profile)
            commands.extend(cmds)

        self._scheduler.schedule(commands)
        logger.info("choreography pattern=%s beats_scheduled=%d devices=%d",
                    active_pattern, len(audio_features.beat_grid), len(self._devices))

    def play_with_position(self, audio_features: AudioFeatures, profile: dict, position_s: float):
        """Schedule commands with known playback position offset."""
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
                continue
            if beat_wall_clock > now + 30:
                break
            cmds = compute_commands(active_pattern, self._devices, beat_wall_clock, profile)
            commands.extend(cmds)
        self._scheduler.schedule(commands)

    def stop(self):
        self._scheduler.clear()
        self._scheduler.stop()
```

- [ ] **Step 2: Commit**

```bash
git add bridge/choreography/layer.py
git commit -m "feat: ChoreographyLayer — orchestrates registry, patterns, and scheduler"
```

---

## Task 11: MusicDataProvider — Spotify (Tier 1)

**Files:**
- Create: `bridge/music/provider.py`
- Create: `bridge/music/spotify.py`
- Test: `tests/test_music_provider.py` (partial, extended in Task 13)

- [ ] **Step 1: Create `bridge/music/provider.py`**

```python
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
```

- [ ] **Step 2: Write failing test for Spotify provider**

```python
# tests/test_music_provider.py
import pytest
from bridge.music.spotify import SpotifyProvider
from bridge.music.types import AudioFeatures

MOCK_FEATURES = {
    "tempo": 128.0, "energy": 0.9, "valence": 0.7,
    "danceability": 0.85, "id": "track123"
}
MOCK_ANALYSIS = {
    "beats": [
        {"start": 0.5, "duration": 0.47, "confidence": 0.9},
        {"start": 0.97, "duration": 0.47, "confidence": 0.85},
        {"start": 1.44, "duration": 0.47, "confidence": 0.95},
    ]
}

def test_spotify_returns_audio_features(requests_mock):
    requests_mock.get(
        "https://api.spotify.com/v1/audio-features/track123",
        json=MOCK_FEATURES,
    )
    requests_mock.get(
        "https://api.spotify.com/v1/audio-analysis/track123",
        json=MOCK_ANALYSIS,
    )
    provider = SpotifyProvider()
    result = provider.fetch("track123", access_token="fake_token")
    assert isinstance(result, AudioFeatures)
    assert result.bpm == 128.0
    assert result.energy == 0.9
    assert len(result.beat_grid) == 3
    assert result.source_tier == 1

def test_spotify_returns_none_on_403(requests_mock):
    requests_mock.get(
        "https://api.spotify.com/v1/audio-features/track123",
        status_code=403,
    )
    provider = SpotifyProvider()
    result = provider.fetch("track123", access_token="fake_token")
    assert result is None
```

Note: Install `requests-mock` for these tests: `pip install requests-mock pytest-requests-mock`

- [ ] **Step 3: Run to verify failure**

```bash
pip install requests-mock
pytest tests/test_music_provider.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.music.spotify'`

- [ ] **Step 4: Create `bridge/music/spotify.py`**

```python
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
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_music_provider.py -v
```

Expected: PASS (2 tests)

- [ ] **Step 6: Commit**

```bash
git add bridge/music/provider.py bridge/music/spotify.py tests/test_music_provider.py
git commit -m "feat: MusicDataProvider ABC + SpotifyProvider (tier 1)"
```

---

## Task 12: MusicDataProvider — Third-Party + Mic + Chain

**Files:**
- Create: `bridge/music/third_party.py`
- Create: `bridge/music/microphone.py`
- Modify: `tests/test_music_provider.py` (add tests)

- [ ] **Step 1: Add tests to `tests/test_music_provider.py`**

Append to the file:

```python
from bridge.music.third_party import ThirdPartyProvider
from bridge.music.microphone import MicrophoneProvider
from bridge.music.provider import chain

MOCK_GETSONGBPM = {
    "search": [{"song_title": "Test Song", "tempo": "120", "artist": {"name": "Test"}}]
}

def test_third_party_returns_audio_features(requests_mock):
    requests_mock.get(
        "https://api.getsongbpm.com/search/",
        json=MOCK_GETSONGBPM,
    )
    provider = ThirdPartyProvider(api_key="test_key")
    result = provider.fetch("track123", title="Test Song", artist="Test")
    assert isinstance(result, AudioFeatures)
    assert result.bpm == 120.0
    assert result.source_tier == 2

def test_third_party_returns_none_on_empty_results(requests_mock):
    requests_mock.get("https://api.getsongbpm.com/search/", json={"search": []})
    provider = ThirdPartyProvider(api_key="test_key")
    result = provider.fetch("track123", title="Unknown", artist="Unknown")
    assert result is None

def test_chain_falls_through_to_tier2(mocker):
    p1 = mocker.MagicMock()
    p1.fetch.return_value = None
    p2 = mocker.MagicMock()
    p2.fetch.return_value = AudioFeatures(
        bpm=120.0, energy=0.7, valence=0.5, mood_tag="calm",
        beat_grid=[], source_tier=2
    )
    result = chain([p1, p2], "track123", access_token="tok")
    assert result.source_tier == 2
    p1.fetch.assert_called_once()
    p2.fetch.assert_called_once()

def test_chain_returns_none_when_all_fail(mocker):
    providers = [mocker.MagicMock(fetch=lambda *a, **k: None) for _ in range(3)]
    result = chain(providers, "track123")
    assert result is None

def test_microphone_provider_returns_audio_features(mocker):
    mock_audio = mocker.MagicMock()
    mocker.patch("bridge.music.microphone.sd.rec", return_value=mock_audio)
    mocker.patch("bridge.music.microphone.sd.wait")
    mocker.patch("bridge.music.microphone.np.array", return_value=mock_audio)
    mock_audio.flatten.return_value = mock_audio
    mocker.patch("bridge.music.microphone.librosa.beat.beat_track",
                 return_value=(128.0, [0.5, 1.0, 1.5]))
    mocker.patch("bridge.music.microphone.librosa.frames_to_time",
                 return_value=[0.5, 1.0, 1.5])
    provider = MicrophoneProvider(record_duration=1)
    result = provider.fetch("any_track_id")
    assert isinstance(result, AudioFeatures)
    assert result.bpm == 128.0
    assert result.source_tier == 3
```

- [ ] **Step 2: Create `bridge/music/third_party.py`**

```python
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
```

- [ ] **Step 3: Create `bridge/music/microphone.py`**

```python
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
```

- [ ] **Step 4: Run all music provider tests**

```bash
pytest tests/test_music_provider.py -v
```

Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/music/third_party.py bridge/music/microphone.py tests/test_music_provider.py
git commit -m "feat: ThirdPartyProvider (GetSongBPM), MicrophoneProvider, chain orchestrator"
```

---

## Task 13: Claude Client

**Files:**
- Create: `bridge/claude_client.py`
- Test: `tests/test_claude_client.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_claude_client.py
import json, pytest
from unittest.mock import MagicMock, patch
from bridge.claude_client import ClaudeClient
from bridge.music.types import AudioFeatures

SAMPLE_FEATURES = AudioFeatures(
    bpm=128.0, energy=0.9, valence=0.7, mood_tag="high_energy_positive",
    beat_grid=[], source_tier=1
)
SAMPLE_PROFILE = {
    "profile_name": "energetic_dance", "source": "auto_track",
    "created_at": "2026-04-18T00:00:00Z", "base_colors": ["#ff0080", "#00ffff"],
    "transition_speed_ms": 300, "beat_response": "pulse", "energy_multiplier": 0.9,
    "mood_tag": "high_energy_positive", "pattern_preferences": ["wave_lr", "pulse_all"],
    "composition_rule": "last_write_wins"
}
ROOM_PROFILE = {"floor_plan": {"width_m": 4.0, "length_m": 3.0}, "devices": []}

def test_generate_auto_profile_returns_valid_profile(mocker):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps(SAMPLE_PROFILE))]
    mock_client.messages.create.return_value = mock_response
    mocker.patch("bridge.claude_client.anthropic.Anthropic", return_value=mock_client)

    client = ClaudeClient(api_key="test")
    result = client.generate_auto_profile(SAMPLE_FEATURES, ROOM_PROFILE, ["pulse_all", "wave_lr"])
    assert result["beat_response"] == "pulse"
    assert result["source"] == "auto_track"

def test_generate_theme_profile_returns_valid_profile(mocker):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps({**SAMPLE_PROFILE, "source": "theme"}))]
    mock_client.messages.create.return_value = mock_response
    mocker.patch("bridge.claude_client.anthropic.Anthropic", return_value=mock_client)

    client = ClaudeClient(api_key="test")
    result = client.generate_theme_profile("late night tokyo rain", ROOM_PROFILE, ["pulse_all"])
    assert result["source"] == "theme"

def test_invalid_json_response_raises(mocker):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="not json")]
    mock_client.messages.create.return_value = mock_response
    mocker.patch("bridge.claude_client.anthropic.Anthropic", return_value=mock_client)

    client = ClaudeClient(api_key="test")
    with pytest.raises(ValueError, match="Invalid profile JSON"):
        client.generate_auto_profile(SAMPLE_FEATURES, ROOM_PROFILE, ["pulse_all"])
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_claude_client.py -v
```

Expected: `ModuleNotFoundError: No module named 'bridge.claude_client'`

- [ ] **Step 3: Create `bridge/claude_client.py`**

```python
import json
import logging
from datetime import datetime, timezone
import anthropic
from bridge.music.types import AudioFeatures
from bridge.profiles.types import validate_profile

logger = logging.getLogger("lumiq")

_SYSTEM_PROMPT = """You are a lighting profile designer for Lumiq, a smart home music-sync system.
Given a track's audio features and the room's device layout, generate a JSON lighting profile.
Use only pattern names from the provided pattern registry.
Return ONLY valid JSON matching this schema — no markdown, no explanation:
{
  "profile_name": "<descriptive_slug_underscores>",
  "source": "<auto_track or theme>",
  "created_at": "<ISO8601>",
  "base_colors": ["<hex>", "<hex>", "<hex>"],
  "transition_speed_ms": <int 200-2000>,
  "beat_response": "<breathe|pulse|sweep|strobe|none>",
  "energy_multiplier": <float 0.0-1.0>,
  "mood_tag": "<string>",
  "pattern_preferences": ["<pattern_name>", ...],
  "composition_rule": "last_write_wins"
}"""

class ClaudeClient:
    def __init__(self, api_key: str):
        self._client = anthropic.Anthropic(api_key=api_key)

    def _call(self, user_prompt: str, source: str) -> dict:
        response = self._client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=[{
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
        try:
            profile = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid profile JSON from Claude: {e}\nRaw: {text[:200]}")
        if not profile.get("created_at"):
            profile["created_at"] = datetime.now(timezone.utc).isoformat()
        profile["source"] = source
        validate_profile(profile)
        return profile

    def generate_auto_profile(
        self, features: AudioFeatures, room_profile: dict, pattern_registry: list
    ) -> dict:
        prompt = (
            f"Track audio features:\n{json.dumps({'bpm': features.bpm, 'energy': features.energy, "
            f"'valence': features.valence, 'mood_tag': features.mood_tag}, indent=2)}\n\n"
            f"Room: {json.dumps(room_profile.get('floor_plan', {}))}\n"
            f"Device count: {len(room_profile.get('devices', []))}\n"
            f"Available patterns: {json.dumps(pattern_registry)}\n\n"
            f"Generate an auto_track lighting profile."
        )
        return self._call(prompt, "auto_track")

    def generate_theme_profile(
        self, vibe_text: str, room_profile: dict, pattern_registry: list
    ) -> dict:
        prompt = (
            f"Vibe description: \"{vibe_text}\"\n\n"
            f"Room: {json.dumps(room_profile.get('floor_plan', {}))}\n"
            f"Device count: {len(room_profile.get('devices', []))}\n"
            f"Available patterns: {json.dumps(pattern_registry)}\n\n"
            f"Generate a theme lighting profile matching this vibe."
        )
        return self._call(prompt, "theme")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_claude_client.py -v
```

Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add bridge/claude_client.py tests/test_claude_client.py
git commit -m "feat: ClaudeClient — Haiku 4.5 with prompt caching for auto and theme profiles"
```

---

## Task 14: AppState + Preset JSON files

**Files:**
- Create: `bridge/state.py`
- Create: `bridge/profiles/presets.py`
- Create: `profiles/presets/club.json`
- Create: `profiles/presets/lounge.json`
- Create: `profiles/presets/party.json`
- Create: `profiles/presets/chill.json`
- Create: `profiles/presets/concert.json`

- [ ] **Step 1: Create preset JSON files**

`profiles/presets/club.json`:
```json
{
  "profile_name": "club", "source": "preset",
  "created_at": "2026-04-18T00:00:00Z",
  "base_colors": ["#ff0080", "#8000ff", "#0080ff"],
  "transition_speed_ms": 200, "beat_response": "strobe",
  "energy_multiplier": 1.0, "mood_tag": "high_energy",
  "pattern_preferences": ["pulse_all", "alternate_zones"],
  "composition_rule": "last_write_wins"
}
```

`profiles/presets/lounge.json`:
```json
{
  "profile_name": "lounge", "source": "preset",
  "created_at": "2026-04-18T00:00:00Z",
  "base_colors": ["#ff8c00", "#b03000", "#800020"],
  "transition_speed_ms": 1200, "beat_response": "breathe",
  "energy_multiplier": 0.4, "mood_tag": "warm_relaxed",
  "pattern_preferences": ["breathe_all", "pulse_all"],
  "composition_rule": "last_write_wins"
}
```

`profiles/presets/party.json`:
```json
{
  "profile_name": "party", "source": "preset",
  "created_at": "2026-04-18T00:00:00Z",
  "base_colors": ["#ff0000", "#00ff00", "#0000ff", "#ffff00"],
  "transition_speed_ms": 300, "beat_response": "pulse",
  "energy_multiplier": 0.9, "mood_tag": "festive",
  "pattern_preferences": ["wave_lr", "alternate_zones", "pulse_all"],
  "composition_rule": "last_write_wins"
}
```

`profiles/presets/chill.json`:
```json
{
  "profile_name": "chill", "source": "preset",
  "created_at": "2026-04-18T00:00:00Z",
  "base_colors": ["#001a4d", "#003366", "#1a3366"],
  "transition_speed_ms": 2000, "beat_response": "breathe",
  "energy_multiplier": 0.3, "mood_tag": "calm_nocturnal",
  "pattern_preferences": ["breathe_all"],
  "composition_rule": "last_write_wins"
}
```

`profiles/presets/concert.json`:
```json
{
  "profile_name": "concert", "source": "preset",
  "created_at": "2026-04-18T00:00:00Z",
  "base_colors": ["#ffffff", "#ffff80", "#ff8000"],
  "transition_speed_ms": 400, "beat_response": "pulse",
  "energy_multiplier": 0.85, "mood_tag": "live_performance",
  "pattern_preferences": ["radial", "wave_lr", "pulse_all"],
  "composition_rule": "last_write_wins"
}
```

- [ ] **Step 2: Create `bridge/profiles/presets.py`**

```python
import json
import os
from typing import Optional

_PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "profiles", "presets")
PRESET_NAMES = {"club", "lounge", "party", "chill", "concert"}

def load_preset(name: str) -> Optional[dict]:
    if name not in PRESET_NAMES:
        return None
    path = os.path.normpath(os.path.join(_PRESETS_DIR, f"{name}.json"))
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)
```

- [ ] **Step 3: Create `bridge/state.py`**

```python
import threading
from typing import Optional

class AppState:
    def __init__(self):
        self._lock = threading.Lock()
        self.mode: str = "preset:chill"     # "preset:<name>" | "auto" | "theme:<slug>"
        self.active_track_id: Optional[str] = None
        self.active_profile: Optional[dict] = None
        self.last_music_tier: Optional[int] = None
        self.bulb_status: dict = {}          # device_id → online bool

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
```

- [ ] **Step 4: Commit**

```bash
git add profiles/presets/ bridge/profiles/presets.py bridge/state.py
git commit -m "feat: preset JSON files (5 profiles) and AppState singleton"
```

---

## Task 15: Flask App + All Routes

**Files:**
- Create: `bridge/app.py`
- Create: `bridge/routes/health.py`
- Create: `bridge/routes/mode.py`
- Create: `bridge/routes/room.py`
- Create: `bridge/routes/track.py`
- Create: `bridge/routes/theme.py`
- Create: `bridge/routes/cron.py`

- [ ] **Step 1: Create `bridge/app.py`**

```python
import os
from flask import Flask
from bridge.config import Config
from bridge.logger import setup_logger
from bridge.state import get_state
from bridge.lights.room import RoomStore
from bridge.lights.controller import LightController
from bridge.profiles.cache import ProfileCache
from bridge.claude_client import ClaudeClient
from bridge.choreography.layer import ChoreographyLayer
from bridge.music.provider import chain as provider_chain
from bridge.music.spotify import SpotifyProvider
from bridge.music.third_party import ThirdPartyProvider
from bridge.music.microphone import MicrophoneProvider

def create_app(config: Config = None) -> Flask:
    if config is None:
        config = Config.from_env()
    setup_logger(config.log_path)

    app = Flask(__name__)
    app.config["LUMIQ_CONFIG"] = config

    # Initialize shared services
    room_store = RoomStore(config.room_profile_path)
    devices = room_store.get_devices()

    cache = ProfileCache(config.profiles_dir)
    claude = ClaudeClient(api_key=config.claude_api_key)

    controller = LightController(devices)
    choreo = ChoreographyLayer(send_fn=controller.send_command)
    choreo.update_devices(devices)

    providers = []
    if config.use_spotify_features:
        providers.append(SpotifyProvider())
    providers.append(ThirdPartyProvider(api_key=config.getsongbpm_api_key))
    providers.append(MicrophoneProvider())

    app.config.update({
        "room_store": room_store,
        "cache": cache,
        "claude": claude,
        "controller": controller,
        "choreo": choreo,
        "providers": providers,
    })

    from bridge.routes.health import bp as health_bp
    from bridge.routes.mode import bp as mode_bp
    from bridge.routes.room import bp as room_bp
    from bridge.routes.track import bp as track_bp
    from bridge.routes.theme import bp as theme_bp
    from bridge.routes.cron import bp as cron_bp
    for blueprint in (health_bp, mode_bp, room_bp, track_bp, theme_bp, cron_bp):
        app.register_blueprint(blueprint)

    return app

if __name__ == "__main__":
    cfg = Config.from_env()
    application = create_app(cfg)
    application.run(host="0.0.0.0", port=cfg.bridge_port, debug=False)
```

- [ ] **Step 2: Create `bridge/routes/health.py`**

```python
from flask import Blueprint, jsonify, current_app
from bridge.state import get_state

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    state = get_state()
    room_store = current_app.config["room_store"]
    devices = room_store.get_devices()
    return jsonify({
        "status": "ok",
        "devices_total": len(devices),
        "devices_online": sum(1 for d in devices if d.online),
        **state.to_health_dict(),
    })
```

- [ ] **Step 3: Create `bridge/routes/mode.py`**

```python
from flask import Blueprint, jsonify, request, current_app
from bridge.state import get_state
from bridge.profiles.presets import PRESET_NAMES

bp = Blueprint("mode", __name__)

@bp.get("/mode")
def get_mode():
    return jsonify({"mode": get_state().mode})

@bp.post("/mode")
def set_mode():
    data = request.get_json(force=True)
    mode = data.get("mode", "")
    # Validate mode format: "preset:<name>" | "auto" | "theme:<slug>"
    valid = (
        mode == "auto"
        or (mode.startswith("preset:") and mode.split(":")[1] in PRESET_NAMES)
        or mode.startswith("theme:")
    )
    if not valid:
        return jsonify({"error": f"Invalid mode: {mode}"}), 400
    get_state().set_mode(mode)
    return jsonify({"mode": mode})
```

- [ ] **Step 4: Create `bridge/routes/room.py`**

```python
from flask import Blueprint, jsonify, request, current_app
from bridge.lights.types import Device

bp = Blueprint("room", __name__)

@bp.get("/room")
def get_room():
    room_store = current_app.config["room_store"]
    devices = room_store.get_devices()
    return jsonify({
        "floor_plan": room_store.get_floor_plan(),
        "devices": [d.__dict__ for d in devices],
    })

@bp.post("/room")
def save_room():
    room_store = current_app.config["room_store"]
    data = request.get_json(force=True)
    devices = [Device(**d) for d in data["devices"]]
    room_store.save(data["floor_plan"], devices)
    current_app.config["controller"].update_devices(devices)
    current_app.config["choreo"].update_devices(devices)
    return jsonify({"saved": True, "device_count": len(devices)})

@bp.post("/room/blink/<device_id>")
def blink(device_id):
    controller = current_app.config["controller"]
    try:
        controller.blink(device_id)
        return jsonify({"blinked": device_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.post("/room/calibrate")
def calibrate():
    room_store = current_app.config["room_store"]
    controller = current_app.config["controller"]
    results = {}
    for device in room_store.get_devices():
        try:
            latency_ms = controller.measure_latency(device.id)
            room_store.update_device(device.id, latency_ms=latency_ms)
            results[device.id] = latency_ms
        except Exception as e:
            results[device.id] = f"error: {e}"
    return jsonify({"latencies_ms": results})
```

- [ ] **Step 5: Create `bridge/routes/track.py`**

```python
import logging
from flask import Blueprint, jsonify, request, current_app
from bridge.music.types import AudioFeatures, BeatEvent
from bridge.music.provider import chain as provider_chain
from bridge.profiles.presets import load_preset
from bridge.choreography.registry import load_registry
from bridge.state import get_state

bp = Blueprint("track", __name__)
logger = logging.getLogger("lumiq")

@bp.post("/track")
def track_change():
    data = request.get_json(force=True)
    track_id = data.get("track_id", "")
    position_ms = data.get("position_ms", 0)
    is_playing = data.get("is_playing", True)
    access_token = data.get("access_token", "")

    if not is_playing:
        current_app.config["choreo"].stop()
        return jsonify({"status": "paused"})

    state = get_state()
    state.set_track(track_id)
    cache = current_app.config["cache"]
    claude = current_app.config["claude"]
    choreo = current_app.config["choreo"]
    room_store = current_app.config["room_store"]
    providers = current_app.config["providers"]
    mode = state.mode
    features: AudioFeatures | None = None  # fetched once, reused for both profile and choreo

    # Resolve profile
    profile = None
    if mode.startswith("preset:"):
        preset_name = mode.split(":", 1)[1]
        profile = load_preset(preset_name)
    elif mode.startswith("theme:"):
        slug = mode.split(":", 1)[1]
        profile = cache.get("themes", slug)
    else:  # auto
        profile = cache.get("tracks", track_id)
        # Always fetch features for auto mode — needed for choreography beat grid
        features = provider_chain(providers, track_id, access_token=access_token)
        if features:
            state.last_music_tier = features.source_tier
        if profile is None and features:
            registry = [p["name"] for p in load_registry()]
            room_profile = {
                "floor_plan": room_store.get_floor_plan(),
                "devices": [d.__dict__ for d in room_store.get_devices()],
            }
            try:
                profile = claude.generate_auto_profile(features, room_profile, registry)
                cache.put("tracks", track_id, profile)
            except Exception as e:
                logger.error("Claude auto profile error: %s", e)

    if profile is None:
        profile = load_preset("chill")  # safe fallback for any failure path

    state.active_profile = profile

    # Hand off to choreography — use real beat grid if available, synthetic otherwise
    if features and features.beat_grid:
        choreo.play_with_position(features, profile, position_ms / 1000.0)
    else:
        choreo.play_with_position(
            _synthetic_beat_features(profile.get("transition_speed_ms", 500)),
            profile,
            position_ms / 1000.0,
        )

    logger.info("track mode=%s track_id=%s profile=%s tier=%s",
                mode, track_id, profile.get("profile_name"), state.last_music_tier)
    return jsonify({"status": "playing", "profile": profile.get("profile_name")})

def _synthetic_beat_features(transition_ms: int) -> AudioFeatures:
    """Beat grid for preset/theme modes that have no real Spotify beat data."""
    beat_interval = transition_ms / 1000.0
    beats = [
        BeatEvent(start=i * beat_interval, duration=beat_interval, confidence=1.0)
        for i in range(240)  # ~4 minutes at given interval
    ]
    return AudioFeatures(
        bpm=60000 / transition_ms, energy=0.7, valence=0.5,
        mood_tag="synthetic", beat_grid=beats, source_tier=0,
    )
```

- [ ] **Step 6: Create `bridge/routes/theme.py`**

```python
import re
from flask import Blueprint, jsonify, request, current_app
from bridge.choreography.registry import load_registry

bp = Blueprint("theme", __name__)

@bp.post("/theme")
def generate_theme():
    data = request.get_json(force=True)
    prompt = data.get("prompt", "").strip()
    if len(prompt) < 3 or len(prompt) > 200:
        return jsonify({"error": "Prompt must be 3–200 characters"}), 400

    slug = re.sub(r"[^a-z0-9]+", "_", prompt.lower())[:50].strip("_")
    cache = current_app.config["cache"]
    existing = cache.get("themes", slug)
    if existing:
        return jsonify({"profile": existing, "cached": True})

    claude = current_app.config["claude"]
    room_store = current_app.config["room_store"]
    registry = [p["name"] for p in load_registry()]
    room_profile = {
        "floor_plan": room_store.get_floor_plan(),
        "devices": [d.__dict__ for d in room_store.get_devices()],
    }
    profile = claude.generate_theme_profile(prompt, room_profile, registry)
    cache.put("themes", slug, profile)
    return jsonify({"profile": profile, "cached": False, "slug": slug})
```

- [ ] **Step 7: Create `bridge/routes/cron.py`**

```python
from flask import Blueprint, jsonify

bp = Blueprint("cron", __name__)

@bp.post("/cron/run-now")
def cron_run_now():
    return jsonify({"error": "Self-improvement cron not implemented in MVP"}), 501
```

- [ ] **Step 8: Run a basic import check**

```bash
cd "E:/Claude Projects/Lumiq"
python -c "from bridge.app import create_app; print('app imports ok')"
```

Expected: `app imports ok`

- [ ] **Step 9: Commit**

```bash
git add bridge/app.py bridge/routes/ bridge/state.py
git commit -m "feat: Flask app factory with all routes — health, mode, room, track, theme, cron stub"
```

---

## Task 16: Integration Smoke Test (Critical Path)

**Files:**
- Modify: `tests/test_integration_critical_path.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/test_integration_critical_path.py
"""
Critical path smoke test:
  POST /track → SpotifyProvider (mocked) → ClaudeClient (mocked)
  → ChoreographyLayer → LightController (mocked) → commands arrive in order
"""
import json
import time
import pytest
from bridge.app import create_app
from bridge.config import Config

MOCK_FEATURES_RESP = {
    "tempo": 120.0, "energy": 0.8, "valence": 0.6,
    "danceability": 0.75, "id": "track_test_001"
}
MOCK_ANALYSIS_RESP = {
    "beats": [
        {"start": 0.5, "duration": 0.5, "confidence": 0.9},
        {"start": 1.0, "duration": 0.5, "confidence": 0.9},
        {"start": 1.5, "duration": 0.5, "confidence": 0.9},
    ]
}
MOCK_CLAUDE_PROFILE = {
    "profile_name": "smoke_test_profile", "source": "auto_track",
    "created_at": "2026-04-18T00:00:00Z",
    "base_colors": ["#ff0000", "#0000ff"],
    "transition_speed_ms": 500, "beat_response": "pulse",
    "energy_multiplier": 0.8, "mood_tag": "energetic",
    "pattern_preferences": ["pulse_all"],
    "composition_rule": "last_write_wins"
}

@pytest.fixture
def test_config(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_API_KEY", "test-key")
    monkeypatch.setenv("USE_SPOTIFY_FEATURES", "true")
    monkeypatch.setenv("GETSONGBPM_API_KEY", "")
    return Config(
        claude_api_key="test-key",
        bridge_port=5001,
        profiles_dir=str(tmp_path / "profiles"),
        room_profile_path=str(tmp_path / "room_profile.json"),
        log_path=str(tmp_path / "logs/bridge.log"),
        use_spotify_features=True,
        getsongbpm_api_key="",
    )

@pytest.fixture
def client(test_config, tmp_path, mocker):
    # Mock Spotify API calls
    mocker.patch("bridge.music.spotify.requests.get", side_effect=_mock_spotify_get)
    # Mock Claude API
    mock_claude_response = mocker.MagicMock()
    mock_claude_response.content = [mocker.MagicMock(text=json.dumps(MOCK_CLAUDE_PROFILE))]
    mocker.patch(
        "bridge.claude_client.anthropic.Anthropic",
        return_value=mocker.MagicMock(
            messages=mocker.MagicMock(create=mocker.MagicMock(return_value=mock_claude_response))
        )
    )
    # Mock TinyTuya
    mock_bulb = mocker.MagicMock()
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)

    app = create_app(test_config)
    app.config["TEST"] = True
    return app.test_client(), app, mock_bulb

def _mock_spotify_get(url, **kwargs):
    import unittest.mock as mock
    resp = mock.MagicMock()
    if "audio-features" in url:
        resp.status_code = 200
        resp.json.return_value = MOCK_FEATURES_RESP
    elif "audio-analysis" in url:
        resp.status_code = 200
        resp.json.return_value = MOCK_ANALYSIS_RESP
    else:
        resp.status_code = 404
    return resp

def test_health_endpoint(client):
    flask_client, app, _ = client
    resp = flask_client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"

def test_mode_switch_to_auto(client):
    flask_client, app, _ = client
    resp = flask_client.post("/mode", json={"mode": "auto"})
    assert resp.status_code == 200
    assert resp.get_json()["mode"] == "auto"

def test_track_change_triggers_profile_generation(client):
    flask_client, app, _ = client
    # Set mode to auto
    flask_client.post("/mode", json={"mode": "auto"})
    # POST a track change
    resp = flask_client.post("/track", json={
        "track_id": "track_test_001",
        "position_ms": 0,
        "is_playing": True,
        "access_token": "fake_token",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "playing"
    assert data["profile"] == "smoke_test_profile"

def test_track_cached_on_second_call(client):
    flask_client, app, mock_bulb = client
    flask_client.post("/mode", json={"mode": "auto"})
    # First call — generates profile
    flask_client.post("/track", json={
        "track_id": "track_test_001",
        "position_ms": 0,
        "is_playing": True,
        "access_token": "fake_token",
    })
    # Second call — should use cache, no new Claude call
    cache = app.config["cache"]
    cached = cache.get("tracks", "track_test_001")
    assert cached is not None
    assert cached["profile_name"] == "smoke_test_profile"

def test_preset_mode_no_api_call(client, mocker):
    flask_client, app, _ = client
    flask_client.post("/mode", json={"mode": "preset:club"})
    resp = flask_client.post("/track", json={
        "track_id": "track_abc",
        "position_ms": 0,
        "is_playing": True,
        "access_token": "fake_token",
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["profile"] == "club"

def test_pause_stops_choreography(client):
    flask_client, app, _ = client
    resp = flask_client.post("/track", json={
        "track_id": "track_001",
        "position_ms": 10000,
        "is_playing": False,
        "access_token": "tok",
    })
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "paused"
```

- [ ] **Step 2: Run to verify failure (expected since app not yet wired)**

```bash
pytest tests/test_integration_critical_path.py -v
```

Expected: Some tests may already pass, others may reveal wiring issues to fix.

- [ ] **Step 3: Fix any wiring issues found, then run full suite**

```bash
pytest -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_integration_critical_path.py
git commit -m "test: integration smoke test — full critical path with mocked Spotify and Claude"
```

---

## Task 17: Manual End-to-End Test Checklist + README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create `README.md`**

```markdown
# Lumiq Bridge

Python Flask backend for the Lumiq smart lighting system. Controls Wipro/Tuya bulbs
in sync with music via Spotify, beat detection, and Claude AI lighting profiles.

## Quick Start (Laptop Dev)

1. Clone and install:
   ```bash
   git clone <repo> && cd lumiq
   pip install -r requirements.txt
   ```

2. Copy and fill env:
   ```bash
   cp .env.example .env
   # Edit .env — add CLAUDE_API_KEY at minimum
   ```

3. Extract TinyTuya local keys (required for bulb control):
   - Register at https://iot.tuya.com
   - Link your Wipro Smart app to the Tuya developer account
   - Run: `python -m tinytuya wizard`
   - Copy the `tuya-raw.json` output and note each device's `id`, `ip`, and `local_key`
   - WARNING: `local_key` changes if the bulb is factory-reset — disable auto firmware updates
   
4. Run the bridge:
   ```bash
   python -m bridge.app
   ```

5. Test health:
   ```bash
   curl http://localhost:5000/health
   ```

## Room Setup (via PWA or curl)

```bash
# Save room profile (replace with your actual device values)
curl -X POST http://localhost:5000/room \
  -H "Content-Type: application/json" \
  -d '{
    "floor_plan": {"width_m": 4.0, "length_m": 3.5, "shape": "rectangle"},
    "devices": [
      {"id": "b1", "tuya_id": "YOUR_DEVICE_ID", "local_key": "YOUR_LOCAL_KEY",
       "address": "192.168.1.x", "type": "color_bulb",
       "x": 0.5, "y": 0.5, "zone": "front_left", "latency_ms": 50,
       "online": true, "capabilities": ["rgb", "brightness"]}
    ]
  }'

# Blink a bulb to confirm connection
curl -X POST http://localhost:5000/room/blink/b1

# Measure latency for all devices
curl -X POST http://localhost:5000/room/calibrate
```

## Manual E2E Test Checklist

Run this after every significant change:

- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `POST /mode {"mode": "preset:club"}` returns 200
- [ ] `POST /track` with `is_playing: false` returns `{"status": "paused"}`
- [ ] `POST /track` in preset mode plays club lights (verify bulbs change colour)
- [ ] `POST /mode {"mode": "auto"}` then POST /track with real Spotify token — verify Auto profile generated and cached
- [ ] `POST /theme {"prompt": "late night coding session"}` — verify theme JSON saved to `profiles/themes/`
- [ ] Kill one bulb's power during a show — verify remaining bulbs continue
- [ ] `GET /health` reflects which devices are offline

## Running Tests

```bash
pytest -v
```

## Raspberry Pi Provisioning (When Ready)

1. Flash Raspberry Pi OS Lite (64-bit) to SD card using Raspberry Pi Imager
2. Enable SSH in Imager advanced options; set hostname `lumiq`, wifi SSID/password
3. Boot Pi, SSH in: `ssh pi@lumiq.local`
4. On the Pi:
   ```bash
   sudo apt update && sudo apt install -y python3-pip python3-venv git portaudio19-dev
   git clone <repo> lumiq && cd lumiq
   python3 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env && nano .env   # fill in your keys
   ```
5. Create systemd service for auto-start:
   ```bash
   sudo nano /etc/systemd/system/lumiq-bridge.service
   ```
   ```ini
   [Unit]
   Description=Lumiq Bridge
   After=network.target
   
   [Service]
   User=pi
   WorkingDirectory=/home/pi/lumiq
   ExecStart=/home/pi/lumiq/venv/bin/python -m bridge.app
   Restart=always
   RestartSec=5
   
   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl enable lumiq-bridge
   sudo systemctl start lumiq-bridge
   sudo systemctl status lumiq-bridge
   ```
6. Assign the Pi a static IP in your router's DHCP settings (use the Pi's MAC address)
7. Confirm bridge is accessible from your laptop: `curl http://<pi-ip>:5000/health`
```

- [ ] **Step 2: Run the full test suite one final time**

```bash
pytest -v --tb=short
```

Expected: All tests PASS with no failures.

- [ ] **Step 3: Final commit**

```bash
git add README.md
git commit -m "docs: README with dev quickstart, TinyTuya setup, Pi provisioning runbook, e2e checklist"
```

---

## Test Coverage Summary

| Module | Tests |
|--------|-------|
| Config | test_config.py (2) |
| Types + validation | test_types.py (3) |
| RoomStore | test_room_store.py (4) |
| LightController | test_lights_controller.py (4) |
| ProfileCache | test_profile_cache.py (5) |
| Pattern registry | test_choreography_registry.py (6) |
| Pattern math | test_choreography_patterns.py (5) |
| Beat scheduler | test_choreography_scheduler.py (3) |
| MusicDataProvider chain | test_music_provider.py (8) |
| ClaudeClient | test_claude_client.py (3) |
| Integration critical path | test_integration_critical_path.py (5) |
| **Total** | **48 tests** |

---

## What Plan 2 Covers (PWA)

Plan 2 builds the React + Tailwind PWA deployed on Vercel:
- Spotify PKCE OAuth and currently-playing poller
- Mode picker, Preset grid, Theme input + library
- Room Setup: floor-plan sketcher + blink-to-identify bulb placement
- All 4 bridge status UI states (Connected / Degraded / Partial / Error)
- Settings screen (bridge URL, key status, cache management)
- Service Worker + PWA manifest for iPhone install

Plan 2 can be started once `GET /health` returns 200 on the bridge.
