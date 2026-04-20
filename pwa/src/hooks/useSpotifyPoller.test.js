import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useSpotifyPoller } from './useSpotifyPoller.js';
import { useStore } from '../store/useStore.js';

const TRACK = { id: 'tid', name: 'Midnight Rain', artists: [{ name: 'Taylor Swift' }] };
const spotifyResponse = { ok: true, status: 200, json: () => Promise.resolve({ is_playing: true, progress_ms: 10000, item: TRACK }) };
const bridgeResponse = { ok: true, json: () => Promise.resolve({ status: 'playing', profile: 'chill' }) };

beforeEach(() => {
  vi.stubEnv('VITE_SPOTIFY_CLIENT_ID', 'test_client');
  useStore.setState({
    bridgeUrl: 'http://localhost:5000',
    accessToken: 'tok',
    refreshToken: 'ref',
    expiresAt: Date.now() + 3_600_000,
    currentTrack: null,
  });
});

afterEach(() => vi.restoreAllMocks());

describe('useSpotifyPoller', () => {
  it('polls Spotify and pushes new track to bridge', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce(spotifyResponse)
      .mockResolvedValueOnce(bridgeResponse);

    renderHook(() => useSpotifyPoller());

    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));
    expect(global.fetch.mock.calls[0][0]).toContain('api.spotify.com');
    expect(global.fetch.mock.calls[1][0]).toBe('http://localhost:5000/track');
    expect(useStore.getState().currentTrack?.id).toBe('tid');
  });

  it('does not push to bridge when track is unchanged', async () => {
    useStore.setState({ ...useStore.getState() });
    global.fetch = vi.fn().mockResolvedValue(spotifyResponse);

    // First render — track is new, bridge gets a push
    renderHook(() => useSpotifyPoller());
    await waitFor(() => expect(global.fetch).toHaveBeenCalledTimes(2));

    const callCount = global.fetch.mock.calls.length;
    // fetchSpy only returns spotify response from here on (no bridge call expected)
    global.fetch.mockClear();
    global.fetch.mockResolvedValue(spotifyResponse);

    // Wait for second poll cycle (3001ms)
    await new Promise((r) => setTimeout(r, 3100));
    // Only Spotify polled, no second bridge push
    expect(global.fetch.mock.calls.filter((c) => c[0].includes('localhost:5000')).length).toBe(0);
  });

  it('skips when no access token', async () => {
    useStore.setState({ accessToken: null });
    global.fetch = vi.fn();
    renderHook(() => useSpotifyPoller());
    await new Promise((r) => setTimeout(r, 50));
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('skips when no bridgeUrl', async () => {
    useStore.setState({ bridgeUrl: '' });
    global.fetch = vi.fn();
    renderHook(() => useSpotifyPoller());
    await new Promise((r) => setTimeout(r, 50));
    expect(global.fetch).not.toHaveBeenCalled();
  });
});
