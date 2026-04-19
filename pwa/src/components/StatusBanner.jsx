import { useStore } from '../store/useStore.js';

const STATES = {
  idle:      { label: 'Connecting…',        cls: 'bg-zinc-800 text-zinc-400' },
  connected: { label: 'Connected',           cls: 'bg-green-900 text-green-300' },
  degraded:  { label: 'Degraded',            cls: 'bg-yellow-900 text-yellow-300' },
  partial:   { label: 'Some bulbs offline',  cls: 'bg-orange-900 text-orange-300' },
  error:     { label: 'Bridge offline',      cls: 'bg-red-900 text-red-300' },
};

export function StatusBanner() {
  const { status, musicTier, offlineDevices, bridgeError } = useStore((s) => ({
    status: s.status, musicTier: s.musicTier, offlineDevices: s.offlineDevices, bridgeError: s.bridgeError,
  }));
  const { label, cls } = STATES[status] ?? STATES.idle;
  const detail =
    status === 'degraded' ? `Music tier: ${musicTier}` :
    status === 'partial'  ? `${offlineDevices} offline` :
    status === 'error'    ? bridgeError : null;

  return (
    <div className={`px-4 py-2 text-sm flex items-center gap-2 ${cls}`}>
      <span className="font-medium">{label}</span>
      {detail && <span className="opacity-75">— {detail}</span>}
    </div>
  );
}
