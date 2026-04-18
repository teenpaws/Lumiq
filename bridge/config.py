import os
from dataclasses import dataclass
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
