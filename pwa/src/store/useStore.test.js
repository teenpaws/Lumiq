import { describe, it, expect, beforeEach } from 'vitest';
import { act } from '@testing-library/react';
import { useStore } from './useStore.js';

beforeEach(() => {
  useStore.setState({
    bridgeUrl: '', accessToken: null, refreshToken: null, expiresAt: null,
    status: 'idle', mode: 'auto', currentTrack: null, musicTier: null,
    offlineDevices: null, bridgeError: null, lastHealth: null, activeProfile: null,
  });
});

describe('useStore', () => {
  it('setBridgeUrl updates bridgeUrl', () => {
    act(() => useStore.getState().setBridgeUrl('http://192.168.1.50:5000'));
    expect(useStore.getState().bridgeUrl).toBe('http://192.168.1.50:5000');
  });

  it('setTokens stores all token fields', () => {
    act(() => useStore.getState().setTokens({ accessToken: 'a', refreshToken: 'r', expiresAt: 9999 }));
    const { accessToken, refreshToken, expiresAt } = useStore.getState();
    expect(accessToken).toBe('a');
    expect(refreshToken).toBe('r');
    expect(expiresAt).toBe(9999);
  });

  it('setStatus updates status and merges extra fields', () => {
    act(() => useStore.getState().setStatus('degraded', { musicTier: 2 }));
    expect(useStore.getState().status).toBe('degraded');
    expect(useStore.getState().musicTier).toBe(2);
  });

  it('clearAuth nullifies token fields', () => {
    act(() => {
      useStore.getState().setTokens({ accessToken: 'a', refreshToken: 'r', expiresAt: 999 });
      useStore.getState().clearAuth();
    });
    expect(useStore.getState().accessToken).toBeNull();
    expect(useStore.getState().refreshToken).toBeNull();
  });

  it('setCurrentTrack updates currentTrack', () => {
    const track = { id: 'tid', name: 'Song', artist: 'Artist' };
    act(() => useStore.getState().setCurrentTrack(track));
    expect(useStore.getState().currentTrack).toEqual(track);
  });

  it('setMode updates mode', () => {
    act(() => useStore.getState().setMode('preset:club'));
    expect(useStore.getState().mode).toBe('preset:club');
  });
});
