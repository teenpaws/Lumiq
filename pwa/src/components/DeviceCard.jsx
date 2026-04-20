import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';

export function DeviceCard({ device, onBlinked }) {
  const bridgeUrl = useStore((s) => s.bridgeUrl);

  async function handleBlink() {
    await createClient(bridgeUrl).blinkDevice(device.id);
    onBlinked?.(device.id);
  }

  return (
    <div className="flex items-center justify-between py-2 px-3 bg-zinc-800 rounded-lg">
      <div>
        <p className="text-sm font-medium text-zinc-100">{device.id}</p>
        <p className="text-xs text-zinc-500">
          {device.zone} · {device.latency_ms != null ? `${device.latency_ms}ms` : 'uncalibrated'} ·{' '}
          <span className={device.online ? 'text-green-400' : 'text-red-400'}>
            {device.online ? 'online' : 'offline'}
          </span>
        </p>
      </div>
      <button onClick={handleBlink} className="text-xs px-2 py-1 rounded bg-zinc-700 text-zinc-300 hover:bg-zinc-600">
        Blink
      </button>
    </div>
  );
}
