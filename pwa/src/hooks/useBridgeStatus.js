import { useEffect } from 'react';
import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';

const HEALTH_POLL_MS = 5000;

export function useBridgeStatus() {
  const bridgeUrl = useStore((s) => s.bridgeUrl);
  const setStatus = useStore((s) => s.setStatus);

  useEffect(() => {
    if (!bridgeUrl) return;
    const client = createClient(bridgeUrl);

    async function check() {
      try {
        const h = await client.getHealth();
        const offline = h.devices_total - h.devices_online;
        if (offline > 0) {
          setStatus('partial', { offlineDevices: offline, lastHealth: h });
        } else if (h.last_music_tier > 0) {
          setStatus('degraded', { musicTier: h.last_music_tier, lastHealth: h });
        } else {
          setStatus('connected', { lastHealth: h });
        }
      } catch {
        setStatus('error', { bridgeError: 'Bridge unreachable' });
      }
    }

    check();
    const id = setInterval(check, HEALTH_POLL_MS);
    return () => clearInterval(id);
  }, [bridgeUrl]);
}
