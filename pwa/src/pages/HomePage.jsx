import { useState, useEffect, useRef } from 'react';
import { useSpotifyPoller } from '../hooks/useSpotifyPoller.js';
import { useBridgeStatus } from '../hooks/useBridgeStatus.js';
import { StatusBanner } from '../components/StatusBanner.jsx';
import { ModePanel } from '../components/ModePanel.jsx';
import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';
import { buildAuthUrl } from '../auth/pkce.js';

const MIC_INTERVAL_MS = 8000;

export function HomePage() {
  useSpotifyPoller();
  useBridgeStatus();
  const { currentTrack, accessToken, bridgeUrl } = useStore((s) => ({
    currentTrack: s.currentTrack,
    accessToken: s.accessToken,
    bridgeUrl: s.bridgeUrl,
  }));
  const [micSync, setMicSync] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!micSync || !bridgeUrl) return;
    const client = createClient(bridgeUrl);
    // Fire immediately, then repeat every 8s
    client.pushTrack('mic_test', 0, true, '').catch(() => {});
    intervalRef.current = setInterval(() => {
      client.pushTrack('mic_test', 0, true, '').catch(() => {});
    }, MIC_INTERVAL_MS);
    return () => clearInterval(intervalRef.current);
  }, [micSync, bridgeUrl]);

  function toggleMicSync() {
    if (micSync) {
      // Stop
      clearInterval(intervalRef.current);
      if (bridgeUrl) createClient(bridgeUrl).pushTrack('mic_test', 0, false, '').catch(() => {});
    }
    setMicSync((v) => !v);
  }

  async function connectSpotify() {
    const url = await buildAuthUrl(import.meta.env.VITE_SPOTIFY_CLIENT_ID, import.meta.env.VITE_SPOTIFY_REDIRECT_URI);
    window.location.href = url;
  }

  return (
    <div className="min-h-screen bg-zinc-950 flex flex-col pb-14">
      <StatusBanner />
      {!accessToken && (
        <div className="px-4 py-3 bg-zinc-900 border-b border-zinc-800">
          <button onClick={connectSpotify} className="px-4 py-2 rounded-full text-sm font-medium bg-green-600 text-white">
            Connect Spotify
          </button>
        </div>
      )}
      {currentTrack && (
        <div className="px-4 py-3 bg-zinc-900 border-b border-zinc-800">
          <p className="text-sm font-medium text-zinc-100 truncate">{currentTrack.name}</p>
          <p className="text-xs text-zinc-500 truncate">{currentTrack.artist}</p>
        </div>
      )}

      {/* Mic Beat Sync (no Spotify needed) */}
      <div className="px-4 pt-4">
        <button
          onClick={toggleMicSync}
          disabled={!bridgeUrl}
          className={`w-full py-3 rounded-xl text-sm font-semibold transition-colors ${
            micSync
              ? 'bg-purple-600 text-white animate-pulse'
              : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'
          } disabled:opacity-40`}
        >
          {micSync ? '🎙 Syncing to Beat — Tap to Stop' : '🎙 Start Beat Sync (Mic)'}
        </button>
        {micSync && (
          <p className="text-xs text-zinc-500 mt-1 text-center">
            Play music near your laptop · bridge listens every 8s
          </p>
        )}
      </div>

      <ModePanel />
    </div>
  );
}
