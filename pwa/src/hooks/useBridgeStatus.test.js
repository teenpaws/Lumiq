import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useBridgeStatus } from './useBridgeStatus.js';
import { useStore } from '../store/useStore.js';

beforeEach(() => {
  useStore.setState({ bridgeUrl: 'http://localhost:5000', status: 'idle', musicTier: null, offlineDevices: null });
});
afterEach(() => vi.restoreAllMocks());

function health(overrides) {
  return { ok: true, json: () => Promise.resolve({ status: 'ok', devices_total: 2, devices_online: 2, mode: 'auto', active_profile: null, last_music_tier: 0, ...overrides }) };
}

describe('useBridgeStatus', () => {
  it('sets status to connected when all devices online and tier 0', async () => {
    global.fetch = vi.fn().mockResolvedValue(health());
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('connected'));
  });

  it('sets status to degraded when last_music_tier > 0', async () => {
    global.fetch = vi.fn().mockResolvedValue(health({ last_music_tier: 2 }));
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('degraded'));
    expect(useStore.getState().musicTier).toBe(2);
  });

  it('sets status to partial when some devices are offline', async () => {
    global.fetch = vi.fn().mockResolvedValue(health({ devices_total: 3, devices_online: 1 }));
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('partial'));
    expect(useStore.getState().offlineDevices).toBe(2);
  });

  it('sets status to error when bridge is unreachable', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('error'));
    expect(useStore.getState().bridgeError).toBeTruthy();
  });

  it('does not poll when bridgeUrl is empty', async () => {
    useStore.setState({ bridgeUrl: '' });
    global.fetch = vi.fn();
    renderHook(() => useBridgeStatus());
    await new Promise((r) => setTimeout(r, 50));
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
