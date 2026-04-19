import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';

const PRESETS = ['club', 'lounge', 'party', 'chill', 'concert'];

export function ModePanel() {
  const { bridgeUrl, mode, setMode } = useStore((s) => ({ bridgeUrl: s.bridgeUrl, mode: s.mode, setMode: s.setMode }));

  async function switchMode(newMode) {
    if (!bridgeUrl) return;
    await createClient(bridgeUrl).setMode(newMode);
    setMode(newMode);
  }

  return (
    <div className="p-4 space-y-3">
      <h2 className="text-xs uppercase tracking-widest text-zinc-500">Mode</h2>
      <div className="flex flex-wrap gap-2">
        <Btn label="Auto" active={mode === 'auto'} onClick={() => switchMode('auto')} />
        {PRESETS.map((p) => (
          <Btn key={p} label={p[0].toUpperCase() + p.slice(1)} active={mode === `preset:${p}`} onClick={() => switchMode(`preset:${p}`)} />
        ))}
      </div>
    </div>
  );
}

function Btn({ label, active, onClick }) {
  return (
    <button onClick={onClick} className={`px-3 py-1.5 rounded-full text-sm font-medium transition-colors ${active ? 'bg-purple-600 text-white' : 'bg-zinc-800 text-zinc-300 hover:bg-zinc-700'}`}>
      {label}
    </button>
  );
}
