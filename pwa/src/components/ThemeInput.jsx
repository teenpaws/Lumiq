import { useState } from 'react';
import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';

export function ThemeInput({ onThemeApplied }) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { bridgeUrl, setMode } = useStore((s) => ({ bridgeUrl: s.bridgeUrl, setMode: s.setMode }));

  async function handleSubmit(e) {
    e.preventDefault();
    if (prompt.trim().length < 3 || prompt.length > 200) {
      setError('Prompt must be 3–200 characters');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const client = createClient(bridgeUrl);
      const { profile, slug } = await client.generateTheme(prompt.trim());
      await client.setMode(`theme:${slug}`);
      setMode(`theme:${slug}`);
      onThemeApplied?.({ profile, slug });
      setPrompt('');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Describe a vibe… (e.g. late night Tokyo rain)"
        maxLength={200}
        className="w-full bg-zinc-800 text-zinc-100 rounded-lg p-3 text-sm resize-none h-20 focus:outline-none focus:ring-1 focus:ring-purple-500"
      />
      <div className="flex justify-between items-center">
        <span className={`text-xs ${prompt.length > 190 ? 'text-orange-400' : 'text-zinc-500'}`}>{prompt.length}/200</span>
        <button type="submit" disabled={loading || prompt.trim().length < 3} className="px-4 py-1.5 rounded-full text-sm font-medium bg-purple-600 text-white disabled:opacity-50">
          {loading ? 'Generating…' : 'Apply Theme'}
        </button>
      </div>
      {error && <p className="text-red-400 text-xs">{error}</p>}
    </form>
  );
}
