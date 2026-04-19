import { useState } from 'react';
import { ThemeInput } from '../components/ThemeInput.jsx';
import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';

const HISTORY_KEY = 'lumiq-theme-history';

function loadHistory() {
  try { return JSON.parse(localStorage.getItem(HISTORY_KEY)) ?? []; }
  catch { return []; }
}

function saveHistory(history) {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
}

export function ThemePage() {
  const [history, setHistory] = useState(loadHistory);
  const { bridgeUrl, setMode } = useStore((s) => ({ bridgeUrl: s.bridgeUrl, setMode: s.setMode }));

  function onThemeApplied(t) {
    setHistory((prev) => {
      const next = [t, ...prev.filter((h) => h.slug !== t.slug)].slice(0, 10);
      saveHistory(next);
      return next;
    });
  }

  async function reapply(slug) {
    if (!bridgeUrl) return;
    await createClient(bridgeUrl).setMode(`theme:${slug}`);
    setMode(`theme:${slug}`);
  }

  return (
    <div className="p-4 space-y-4 pb-16 min-h-screen bg-zinc-950">
      <h1 className="text-lg font-semibold text-zinc-100">Theme</h1>
      <ThemeInput onThemeApplied={onThemeApplied} />
      {history.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-xs uppercase tracking-widest text-zinc-500">Recent</h2>
          {history.map(({ slug, profile }) => (
            <button key={slug} onClick={() => reapply(slug)}
              className="w-full text-left py-2 px-3 bg-zinc-800 rounded-lg hover:bg-zinc-700 transition-colors">
              <p className="text-sm text-zinc-200">{profile.profile_name ?? slug}</p>
              {profile.mood_tag && <p className="text-xs text-zinc-500">{profile.mood_tag}</p>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
