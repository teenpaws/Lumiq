import { useState } from 'react';
import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';

export function SettingsPage() {
  const { bridgeUrl, setBridgeUrl, accessToken, clearAuth } = useStore((s) => ({
    bridgeUrl: s.bridgeUrl, setBridgeUrl: s.setBridgeUrl, accessToken: s.accessToken, clearAuth: s.clearAuth,
  }));
  const [inputUrl, setInputUrl] = useState(bridgeUrl);
  const [testResult, setTestResult] = useState(null);

  async function handleSave(e) {
    e.preventDefault();
    const url = inputUrl.trim().replace(/\/$/, '');
    setBridgeUrl(url);
    try {
      const h = await createClient(url).getHealth();
      setTestResult({ ok: true, msg: `Connected — ${h.devices_total} devices` });
    } catch {
      setTestResult({ ok: false, msg: 'Could not reach bridge at that URL' });
    }
  }

  return (
    <div className="p-4 space-y-6 pb-16">
      <h1 className="text-lg font-semibold text-zinc-100">Settings</h1>

      <section className="space-y-2">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">Bridge</h2>
        <form onSubmit={handleSave} className="space-y-2">
          <input value={inputUrl} onChange={(e) => setInputUrl(e.target.value)}
            placeholder="http://192.168.1.50:5000"
            className="w-full bg-zinc-800 text-zinc-100 rounded-lg p-3 text-sm focus:outline-none focus:ring-1 focus:ring-purple-500" />
          <button type="submit" className="px-4 py-1.5 rounded-full text-sm font-medium bg-purple-600 text-white">Save & Test</button>
          {testResult && <p className={`text-xs ${testResult.ok ? 'text-green-400' : 'text-red-400'}`}>{testResult.msg}</p>}
        </form>
      </section>

      <section className="space-y-2">
        <h2 className="text-xs uppercase tracking-widest text-zinc-500">Spotify</h2>
        <p className="text-sm text-zinc-400">{accessToken ? 'Authenticated' : 'Not authenticated'}</p>
        {accessToken && (
          <button onClick={clearAuth} className="px-3 py-1 rounded-full text-xs bg-zinc-800 text-zinc-300 hover:bg-zinc-700">
            Sign out
          </button>
        )}
      </section>
    </div>
  );
}
