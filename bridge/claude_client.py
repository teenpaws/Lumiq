# bridge/claude_client.py
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
        # Strip markdown code fences if Claude wraps the JSON
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
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
            f"Track audio features:\n{json.dumps({'bpm': features.bpm, 'energy': features.energy, 'valence': features.valence, 'mood_tag': features.mood_tag}, indent=2)}\n\n"
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
