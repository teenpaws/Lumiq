# bridge/app.py
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
from bridge.music.spotify import SpotifyProvider
from bridge.music.third_party import ThirdPartyProvider
from bridge.music.microphone import MicrophoneProvider

def create_app(config: Config = None) -> Flask:
    if config is None:
        config = Config.from_env()
    setup_logger(config.log_path)

    app = Flask(__name__)
    app.config["LUMIQ_CONFIG"] = config

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
