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
