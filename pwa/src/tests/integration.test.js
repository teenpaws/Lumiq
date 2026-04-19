import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useStore } from '../store/useStore.js';
import { useSpotifyPoller } from '../hooks/useSpotifyPoller.js';
import { useBridgeStatus } from '../hooks/useBridgeStatus.js';

const HEALTH_OK = { status: 'ok', devices_total: 2, devices_online: 2, mode: 'auto', active_profile: null, last_music_tier: 0 };
const HEALTH_DEGRADED = { ...HEALTH_OK, last_music_tier: 2 };
const HEALTH_PARTIAL = { ...HEALTH_OK, devices_online: 1 };
const TRACK_RESPONSE = { is_playing: true, progress_ms: 10000, item: { id: 'tid_xyz', name: 'Midnight Rain', artists: [{ name: 'Taylor Swift' }] } };

beforeEach(() => {
  vi.stubEnv('VITE_SPOTIFY_CLIENT_ID', 'test_client');
  useStore.setState({
    bridgeUrl: 'http://localhost:5000',
    accessToken: 'spotify_token',
    refreshToken: 'refresh_token',
    expiresAt: Date.now() + 3_600_000,
    status: 'idle', currentTrack: null, musicTier: null, offlineDevices: null,
  });
});

afterEach(() => vi.restoreAllMocks());

describe('Integration: useBridgeStatus', () => {
  it('connected — all devices online, tier 0', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(HEALTH_OK) });
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('connected'));
    expect(useStore.getState().lastHealth.devices_total).toBe(2);
  });

  it('degraded — last_music_tier > 0', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(HEALTH_DEGRADED) });
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('degraded'));
    expect(useStore.getState().musicTier).toBe(2);
  });

  it('partial — some bulbs offline', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve(HEALTH_PARTIAL) });
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('partial'));
    expect(useStore.getState().offlineDevices).toBe(1);
  });

  it('error — bridge unreachable', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Failed to fetch'));
    renderHook(() => useBridgeStatus());
    await waitFor(() => expect(useStore.getState().status).toBe('error'));
    expect(useStore.getState().bridgeError).toBeTruthy();
  });
});

describe('Integration: useSpotifyPoller full critical path', () => {
  it('Spotify poll → track change → bridge push → store currentTrack set', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(TRACK_RESPONSE) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ status: 'playing', profile: 'chill' }) });

    renderHook(() => useSpotifyPoller());

    await waitFor(() => expect(useStore.getState().currentTrack?.id).toBe('tid_xyz'));
    expect(global.fetch).toHaveBeenCalledTimes(2);
    const spotifyCall = global.fetch.mock.calls[0];
    expect(spotifyCall[0]).toContain('api.spotify.com');
    expect(spotifyCall[1].headers.Authorization).toBe('Bearer spotify_token');
    const bridgeCall = global.fetch.mock.calls[1];
    expect(bridgeCall[0]).toBe('http://localhost:5000/track');
    const body = JSON.parse(bridgeCall[1].body);
    expect(body.track_id).toBe('tid_xyz');
    expect(body.position_ms).toBe(10000);
    expect(body.is_playing).toBe(true);
    expect(body.access_token).toBe('spotify_token');
  });

  it('paused track (is_playing false) pushes to bridge with is_playing: false', async () => {
    const paused = { ...TRACK_RESPONSE, is_playing: false };
    global.fetch = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve(paused) })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ status: 'paused' }) });

    renderHook(() => useSpotifyPoller());

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
    expect(JSON.parse(global.fetch.mock.calls[1][1].body).is_playing).toBe(false);
  });

  it('204 response (nothing playing) does not push to bridge', async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 204 });
    renderHook(() => useSpotifyPoller());
    await new Promise((r) => setTimeout(r, 50));
    expect(global.fetch).toHaveBeenCalledTimes(1); // only Spotify, no bridge
  });
});
