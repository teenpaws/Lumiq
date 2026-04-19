import { useSpotifyPoller } from '../hooks/useSpotifyPoller.js';
import { useBridgeStatus } from '../hooks/useBridgeStatus.js';
import { StatusBanner } from '../components/StatusBanner.jsx';
import { ModePanel } from '../components/ModePanel.jsx';
import { useStore } from '../store/useStore.js';
import { buildAuthUrl } from '../auth/pkce.js';

export function HomePage() {
  useSpotifyPoller();
  useBridgeStatus();
  const { currentTrack, accessToken } = useStore((s) => ({ currentTrack: s.currentTrack, accessToken: s.accessToken }));

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
      <ModePanel />
    </div>
  );
}
