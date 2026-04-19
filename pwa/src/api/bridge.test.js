import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createClient } from './bridge.js';

let client;
beforeEach(() => {
  client = createClient('http://localhost:5000');
  global.fetch = vi.fn();
});

function mockOk(data) {
  global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(data) });
}

describe('createClient', () => {
  it('getHealth calls GET /health', async () => {
    mockOk({ status: 'ok', devices_total: 2, devices_online: 2, mode: 'auto', active_profile: null, last_music_tier: 0 });
    const result = await client.getHealth();
    expect(global.fetch).toHaveBeenCalledWith('http://localhost:5000/health', expect.objectContaining({ method: 'GET' }));
    expect(result.status).toBe('ok');
  });

  it('setMode calls POST /mode with body', async () => {
    mockOk({ mode: 'auto' });
    await client.setMode('auto');
    const [, opts] = global.fetch.mock.calls[0];
    expect(opts.method).toBe('POST');
    expect(JSON.parse(opts.body)).toEqual({ mode: 'auto' });
  });

  it('pushTrack calls POST /track with all fields', async () => {
    mockOk({ status: 'playing', profile: 'chill' });
    await client.pushTrack('tid', 45000, true, 'tok');
    const body = JSON.parse(global.fetch.mock.calls[0][1].body);
    expect(body).toEqual({ track_id: 'tid', position_ms: 45000, is_playing: true, access_token: 'tok' });
  });

  it('generateTheme calls POST /theme', async () => {
    mockOk({ profile: { profile_name: 'x' }, slug: 'x', cached: false });
    await client.generateTheme('dark jazz');
    expect(global.fetch.mock.calls[0][0]).toBe('http://localhost:5000/theme');
    expect(JSON.parse(global.fetch.mock.calls[0][1].body).prompt).toBe('dark jazz');
  });

  it('blinkDevice calls POST /room/blink/:id', async () => {
    mockOk({ blinked: 'bulb_01' });
    await client.blinkDevice('bulb_01');
    expect(global.fetch.mock.calls[0][0]).toBe('http://localhost:5000/room/blink/bulb_01');
  });

  it('calibrate calls POST /room/calibrate', async () => {
    mockOk({ latencies_ms: { bulb_01: 42 } });
    const result = await client.calibrate();
    expect(result.latencies_ms.bulb_01).toBe(42);
  });

  it('throws on non-ok response', async () => {
    global.fetch.mockResolvedValue({ ok: false, status: 503 });
    await expect(client.getHealth()).rejects.toThrow('Bridge GET /health → 503');
  });

  it('strips trailing slash from base URL', async () => {
    const c = createClient('http://localhost:5000/');
    mockOk({ status: 'ok' });
    await c.getHealth();
    expect(global.fetch.mock.calls[0][0]).toBe('http://localhost:5000/health');
  });
});
