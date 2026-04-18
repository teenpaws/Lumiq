# Lumiq MVP — Design Spec

**Date:** 2026-04-18
**Status:** Approved via brainstorming
**Source:** `Lumiq_Project_Discussion_v6.docx` (April 2026), narrowed to MVP slice

---

## 1. Scope

### In
- PWA (React + Tailwind) hosted on Vercel, installable on iPhone via Safari
- Spotify OAuth (PKCE) using a pre-Nov-2024 Spotify developer app to retain access to Audio Features + Audio Analysis endpoints
- Three-tier music-data fallback chain:
  1. Spotify Audio Features + Audio Analysis
  2. Third-party API (GetSongBPM or ReccoBeats) keyed by Spotify track ID / ISRC
  3. Local mic-based beat detection via `aubio` or `librosa` on the bridge
- Flask bridge (Python), developed on the user's laptop, later provisioned onto a Raspberry Pi
- Wipro / Tuya color bulbs + smart tubelights via TinyTuya (single protocol)
- Three lighting modes: Presets (5 hardcoded), Auto (Haiku 4.5 generates per-track profile, cached), Theme (Haiku 4.5 generates profile from vibe text, cached forever)
- Choreography Layer — adaptive to the current room: patterns declare requirements; only eligible patterns run
- Room Setup via 2D floor-plan tap placement with blink-to-identify, stores (x, y) + zone + measured latency per device
- Per-bulb latency calibration performed during room setup
- Local JSON profile cache on the bridge (presets + themes + per-track profiles)
- Track-change detection from PWA via Spotify `currently-playing` poll, pushed to bridge over LAN HTTP

### Out (deferred to later phases)
- TV Ambient mode / HDMI capture / TV Vision agent
- Song Library SQLite + weekly Claude self-improvement cron
- Apple Music / YouTube Music / MusicKit integration
- Multi-vendor bulb support (Hue, WLED, Govee, Nanoleaf)
- AR scan via WebXR or native ARKit wrapper
- Multi-user / authentication / client locking
- True multi-agent Orchestrator (MVP runs one mode at a time; the "agents" live as modules in the bridge but are not a dispatched agent system)

---

## 2. Architecture

Two processes: **PWA (browser)** and **Bridge (laptop/Pi)**.

### PWA — React + Tailwind on Vercel
Responsibilities:
- Spotify OAuth (PKCE; redirect URI = Vercel HTTPS URL)
- Currently-playing poller (~3s cadence while active, backs off when idle)
- Mode picker UI: Presets / Auto / Theme
- Theme input + theme library browser
- Room Setup UI: floor-plan sketcher, blink-to-identify bulb placement, latency calibration trigger
- Settings: bridge URL, API key status indicators, cache management
- Service Worker: PWA install shell, network-first app shell, "New version available" prompt on SW update
- State held in the PWA: Spotify access token (localStorage), bridge URL (localStorage), UI state only

The PWA holds no lighting logic; it is a thin remote. This is deliberate so iOS background-throttling cannot break an active show.

### Bridge — Python Flask on laptop (dev) / Raspberry Pi (prod)
Modules:
- **HTTP API** — Flask endpoints (see §6)
- **MusicDataProvider** — three-tier chain with a common interface; config flag disables tier 1 if the Spotify app is unavailable
- **Profile Cache** — filesystem, file-per-entry, keyed under `profiles/{presets,themes,tracks}/`
- **Claude Client** — Haiku 4.5 for Auto profile generation and Theme profile generation
- **Choreography Layer** — see §5
- **Light Controller** — TinyTuya wrapper with per-device command queue and offline detection
- **Room Profile Store** — single `room_profile.json`
- **Pattern Registry** — hardcoded `patterns.json` shipped in the repo
- **Structured logger** — Python `logging` with rotating file handler

### Communication
- PWA ↔ Bridge: plain HTTP on the LAN (e.g., `http://192.168.1.50:5000`)
- Spotify OAuth: PKCE in the PWA; access token forwarded to the bridge with each track-change push so the bridge can call Audio Features / Analysis
- Claude API key and third-party music-data API key live **only** on the bridge, never in the PWA

---

## 3. Data Flow

### Cold start (once)
1. User opens PWA on Vercel → Spotify OAuth → enters bridge LAN URL.
2. Room Setup wizard: sketch floor plan → bridge scans LAN for Tuya devices → user blinks + taps each device onto the plan → bridge measures round-trip latency per device → saves `room_profile.json`.

### Steady state — track plays
1. PWA polls Spotify `/currently-playing` every ~3s.
2. On track change, PWA POSTs `{track_id, position_ms, is_playing, access_token}` to bridge.
3. Bridge checks `profiles/tracks/<track_id>.json`; cache hit → jump to step 6.
4. Cache miss → `MusicDataProvider` chain (Spotify → third-party → mic). Returns `{bpm, energy, valence, beat_grid[], mood_tag}`.
5. Bridge calls Haiku 4.5 with `{audio_features, room_profile, pattern_registry, mode}`; receives profile JSON; saves to cache.
6. Choreography Layer receives profile + beat grid + `position_ms`. Filters to eligible patterns. Schedules per-bulb commands, advanced by each bulb's measured `latency_ms`.
7. Light Controller executes commands via TinyTuya over LAN.

### Mode switches
- **Presets:** read preset JSON; no API call.
- **Theme:** user text → `profiles/themes/<slug>.json` cache hit, or Haiku call + cache write.
- **Auto:** as above.

### Offline / degraded behavior
- No internet → Auto falls back to a deterministic rule-based profile picker (maps cached audio features to a preset family).
- No Spotify → mic tier only; beat-follow without track identity.
- Bulb offline → Choreography Layer recomputes eligible patterns for the remaining bulbs; missed cues are dropped, not retried.
- Bridge unreachable → PWA shows "Bridge offline" state with last-known status.

---

## 4. Data Model

### `room_profile.json`
```json
{
  "floor_plan": {"width_m": 4.2, "length_m": 3.6, "shape": "rectangle"},
  "devices": [
    {
      "id": "bulb_01",
      "tuya_id": "...",
      "local_key": "...",
      "type": "color_bulb",
      "x": 1.2,
      "y": 0.8,
      "zone": "front_left",
      "latency_ms": 42,
      "online": true,
      "capabilities": ["rgb", "brightness", "white"]
    }
  ]
}
```

### Profile JSON (same shape for presets, themes, track profiles)
```json
{
  "profile_name": "late_night_tokyo_rain",
  "source": "theme",
  "created_at": "2026-04-18T00:00:00Z",
  "base_colors": ["#0a1e3f", "#2d4a8b", "#ff4a7d"],
  "transition_speed_ms": 800,
  "beat_response": "breathe",
  "energy_multiplier": 0.6,
  "mood_tag": "calm_nocturnal",
  "pattern_preferences": ["wave_lr", "radial", "breathe_all"],
  "composition_rule": "last_write_wins"
}
```

`source` is one of `preset | theme | auto_track`.
`beat_response` is one of `breathe | pulse | sweep | strobe | none`.
`composition_rule` is one of `last_write_wins | blend | priority`.

### Pattern registry (`patterns.json`, shipped)
```json
[
  {"name": "pulse_all",       "min_bulbs": 1, "requires": [],                     "composable_with": []},
  {"name": "wave_lr",         "min_bulbs": 3, "requires": ["x_coords"],           "composable_with": ["breathe_all"]},
  {"name": "radial",          "min_bulbs": 4, "requires": ["x_coords","y_coords"],"composable_with": []},
  {"name": "alternate_zones", "min_bulbs": 2, "requires": ["zones"],              "composable_with": ["breathe_all"]},
  {"name": "breathe_all",     "min_bulbs": 1, "requires": [],                     "composable_with": ["wave_lr","alternate_zones"]}
]
```

### Filesystem layout (bridge)
```
/lumiq/
  room_profile.json
  profiles/
    presets/       # club, lounge, party, chill, concert — shipped
    themes/<slug>.json
    tracks/<spotify_track_id>.json
  logs/bridge.log  # rotating, 10 MB x 5
  .env             # CLAUDE_API_KEY, SPOTIFY_APP_ID, THIRD_PARTY_KEY, BRIDGE_PORT, USE_SPOTIFY_FEATURES
```

---

## 5. Choreography Layer

The MVP's load-bearing component. Coordinates all devices as a single room-wide show rather than independent per-device reactions.

**Input:** profile JSON + beat grid (timestamped) + current playback position + room profile.
**Output:** a stream of `(device_id, color, brightness, at_timestamp)` commands to the Light Controller.

### Algorithm
1. Filter the pattern registry → eligible patterns = those whose `min_bulbs` and `requires` are satisfied by `room_profile`.
2. Intersect with profile's `pattern_preferences` → ranked list; top entry is active.
3. For each beat in the upcoming 500 ms lookahead window:
   1. Compute per-bulb color + brightness for the active pattern given `beat_timestamp` and device positions.
   2. Schedule each command at `beat_timestamp - device.latency_ms - 50 ms` buffer so it lands just-in-time.
4. On failed command: mark device offline after 3 consecutive failures; recompute eligible patterns; continue.
5. Composition: if two patterns are active simultaneously, `composable_with` gates whether both may run; otherwise fall back to `composition_rule` (default `last_write_wins`).

### Pattern math
- **`wave_lr`** — color sweeps left-to-right across bulbs sorted by `x`. Each bulb lights at `(x_normalized * beat_duration)` after the beat.
- **`radial`** — center = centroid of bulbs. Bulbs lit in order of distance from center per beat.
- **`alternate_zones`** — bulbs grouped by zone; on each beat alternates between zone sets A and B.
- **`pulse_all`** — all bulbs hit the beat color simultaneously.
- **`breathe_all`** — slow sinusoidal brightness ramp, period = 2 bars.

### Latency compensation
Per-device `latency_ms` is measured during Room Setup by sending a known color change and timing the state-read confirmation. Stored in `room_profile.json` and used by the scheduler to pre-advance each command.

---

## 6. Error Handling, Testing, Observability

### PWA UI states (distinct visuals required)
- **Connected** — all green
- **Degraded** — fallback tier active; UI shows which `MusicDataProvider` tier and why
- **Partial** — some bulbs offline; list them with a retry button
- **Error** — bridge unreachable; reconnect prompt + last-known status

### Bridge HTTP API
- `POST /track` — track change notification from PWA
- `GET /mode`, `POST /mode` — read and switch the active mode
- `POST /theme` — generate (or fetch cached) theme profile from a user prompt
- `GET /room`, `POST /room` — read and write room profile
- `POST /room/blink/<device_id>` — blink a bulb during setup
- `POST /room/calibrate` — run per-device latency measurement
- `GET /health` — bridge status, bulb online/offline, last music-data tier used
- `POST /cron/run-now` — reserved for future self-improvement cron; returns 501 in MVP but kept in the API contract

### Testing
- Unit tests per `MusicDataProvider` implementation against mocked API responses
- Unit tests for Choreography Layer pattern math: given `(room_profile, profile, beat_grid)`, assert exact `(device_id, color, brightness, at_timestamp)` output
- Integration smoke test for the critical path: mock track change → mock Spotify features → mock Haiku response → mock TinyTuya → assert command ordering and timing. No hardware required.
- Manual end-to-end test checklist for real-hardware runs on the laptop dev hub.

### Observability
- Python `logging` module, rotating file handler
- Every bulb command, every API call, every fallback trigger logs: timestamp, event type, device_id or API name, result, latency_ms
- `/health` returns the current state consumed by the PWA status indicator
- `logs/bridge.log` rotates at 10 MB, keeps last 5 files

### Dependency discipline
- `requirements.txt` with exact pins (via `pip freeze`)
- `package-lock.json` committed
- `.env.example` documents every variable the bridge and PWA need

### PWA cache strategy
- Service Worker uses network-first for the app shell so updates propagate within one session
- Prompt the user "New version available — tap to update" when a new Service Worker is detected

### Input validation
- Theme prompt: 3–200 characters; strip control and prompt-injection-adjacent characters

---

## 7. Known Risks & Mitigations

- **Spotify Audio Features endpoint access.** Relies on using a pre-Nov-2024 Spotify developer app. If that app becomes unavailable, the `MusicDataProvider` chain automatically falls through to the third-party API and then to mic-based detection. A config flag disables tier 1 cleanly.
- **TinyTuya firmware risk.** Tuya can disable local control via firmware update. Mitigation: disable automatic firmware updates on each bulb once local keys are extracted.
- **iOS PWA background throttling.** When the phone sleeps, track-change detection lags; the bridge continues the active show on the last-known track. A native iOS companion is Phase 2.
- **Spotify ToS grey area.** Using Audio Features for a non-Spotify lighting experience is permissible for personal use; legal review is required before any public distribution.
- **TinyTuya `local_key` extraction** is a documented but fiddly setup step. Full step-by-step instructions will live in the repo README before dev starts.

---

## 8. Explicit Non-Goals for MVP

- No Orchestrator Agent as a separate process; modes are selected directly
- No Agent Registry JSON; the architecture is a modular monolith inside the bridge
- No SQLite in the bridge
- No AR / WebXR / native wrapper
- No song-library preference learning or weekly cron
- No TV mode, no HDMI capture, no vision agent
- No multi-user concurrency / locking
