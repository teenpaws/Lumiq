import { useEffect, useRef } from 'react';
import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';
import { refreshAccessToken } from '../auth/pkce.js';

const POLL_MS = 3000;
const REFRESH_BUFFER_MS = 60_000;

export function useSpotifyPoller() {
  const lastTrackRef = useRef(null);
  const bridgeUrl = useStore((s) => s.bridgeUrl);

  useEffect(() => {
    if (!bridgeUrl) return;
    const bridge = createClient(bridgeUrl);
    let active = true;

    async function poll() {
      if (!active) return;
      const { accessToken, refreshToken, expiresAt, setTokens, setCurrentTrack } = useStore.getState();
      if (!accessToken) return;

      let token = accessToken;
      if (Date.now() >= expiresAt - REFRESH_BUFFER_MS) {
        try {
          const tokens = await refreshAccessToken(refreshToken, import.meta.env.VITE_SPOTIFY_CLIENT_ID);
          setTokens(tokens);
          token = tokens.accessToken;
        } catch {
          return;
        }
      }

      try {
        const res = await fetch('https://api.spotify.com/v1/me/player/currently-playing', {
          headers: { Authorization: `Bearer ${token}` },
          signal: AbortSignal.timeout(4000),
        });
        if (res.status === 204 || !res.ok) return;
        const data = await res.json();
        const trackId = data.item?.id;
        if (!trackId) return;
        setCurrentTrack({ id: trackId, name: data.item.name, artist: data.item.artists[0]?.name });
        if (trackId !== lastTrackRef.current) {
          lastTrackRef.current = trackId;
          await bridge.pushTrack(trackId, data.progress_ms, data.is_playing, token);
        }
      } catch {
        // silence — status managed by useBridgeStatus
      }
    }

    poll();
    const id = setInterval(poll, POLL_MS);
    return () => { active = false; clearInterval(id); };
  }, [bridgeUrl]);
}
