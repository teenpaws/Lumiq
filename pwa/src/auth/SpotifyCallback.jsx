import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { exchangeCode } from './pkce.js';
import { useStore } from '../store/useStore.js';

export function SpotifyCallback() {
  const navigate = useNavigate();
  const setTokens = useStore((s) => s.setTokens);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const error = params.get('error');
    if (error || !code) { navigate('/settings'); return; }

    exchangeCode(code, import.meta.env.VITE_SPOTIFY_CLIENT_ID, import.meta.env.VITE_SPOTIFY_REDIRECT_URI)
      .then((tokens) => { setTokens(tokens); navigate('/'); })
      .catch(() => navigate('/settings'));
  }, []);

  return <div className="p-4 text-zinc-400 text-sm">Connecting to Spotify…</div>;
}
