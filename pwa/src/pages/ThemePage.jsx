import { useState } from 'react';
import { ThemeInput } from '../components/ThemeInput.jsx';

export function ThemePage() {
  const [history, setHistory] = useState([]);

  return (
    <div className="p-4 space-y-4 pb-16 min-h-screen bg-zinc-950">
      <h1 className="text-lg font-semibold text-zinc-100">Theme</h1>
      <ThemeInput onThemeApplied={(t) => setHistory((prev) => [t, ...prev].slice(0, 10))} />
      {history.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-xs uppercase tracking-widest text-zinc-500">Recent</h2>
          {history.map(({ slug, profile }) => (
            <div key={slug} className="py-2 px-3 bg-zinc-800 rounded-lg">
              <p className="text-sm text-zinc-200">{profile.profile_name ?? slug}</p>
              {profile.mood_tag && <p className="text-xs text-zinc-500">{profile.mood_tag}</p>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
