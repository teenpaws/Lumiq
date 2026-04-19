import { describe, it, expect, vi, beforeEach } from 'vitest';
import { generateVerifier, generateChallenge, buildAuthUrl, exchangeCode, refreshAccessToken } from './pkce.js';

beforeEach(() => {
  vi.stubEnv('VITE_SPOTIFY_CLIENT_ID', 'test_client_id');
  vi.stubEnv('VITE_SPOTIFY_REDIRECT_URI', 'https://example.com/callback');
  const store = {};
  vi.stubGlobal('sessionStorage', {
    setItem: (k, v) => { store[k] = v; },
    getItem: (k) => store[k] ?? null,
    removeItem: (k) => { delete store[k]; },
  });
});

describe('generateVerifier', () => {
  it('returns a 86-char base64url string', () => {
    const v = generateVerifier();
    expect(v).toMatch(/^[A-Za-z0-9\-_]+$/);
    expect(v.length).toBe(86);
  });

  it('generates unique values each call', () => {
    expect(generateVerifier()).not.toBe(generateVerifier());
  });
});

describe('generateChallenge', () => {
  it('returns a 43-char base64url string for any verifier', async () => {
    const challenge = await generateChallenge('dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk');
    expect(challenge).toMatch(/^[A-Za-z0-9\-_]+$/);
    expect(challenge.length).toBe(43);
  });
});

describe('buildAuthUrl', () => {
  it('returns a Spotify authorize URL with all required params', async () => {
    const url = await buildAuthUrl('my_client', 'https://example.com/callback');
    expect(url).toContain('https://accounts.spotify.com/authorize');
    expect(url).toContain('client_id=my_client');
    expect(url).toContain('code_challenge_method=S256');
    expect(url).toContain('user-read-currently-playing');
    expect(url).toContain('response_type=code');
  });

  it('stores the verifier in sessionStorage', async () => {
    await buildAuthUrl('client', 'https://example.com/callback');
    expect(sessionStorage.getItem('pkce_verifier')).toBeTruthy();
  });
});

describe('exchangeCode', () => {
  it('POSTs to Spotify token endpoint and returns token data', async () => {
    sessionStorage.setItem('pkce_verifier', 'test_verifier');
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ access_token: 'acc', refresh_token: 'ref', expires_in: 3600 }),
    });
    const result = await exchangeCode('auth_code', 'client_id', 'https://example.com/callback');
    expect(result.accessToken).toBe('acc');
    expect(result.refreshToken).toBe('ref');
    expect(result.expiresAt).toBeGreaterThan(Date.now());
    const [url, opts] = global.fetch.mock.calls[0];
    expect(url).toBe('https://accounts.spotify.com/api/token');
    expect(opts.method).toBe('POST');
  });

  it('throws on non-ok response', async () => {
    sessionStorage.setItem('pkce_verifier', 'v');
    global.fetch = vi.fn().mockResolvedValue({ ok: false, status: 400 });
    await expect(exchangeCode('code', 'client', 'https://example.com/callback')).rejects.toThrow('Token exchange failed: 400');
  });
});

describe('refreshAccessToken', () => {
  it('POSTs refresh_token grant and returns new token data', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ access_token: 'new_acc', expires_in: 3600 }),
    });
    const result = await refreshAccessToken('old_ref', 'client_id');
    expect(result.accessToken).toBe('new_acc');
    expect(result.refreshToken).toBe('old_ref');
  });
});
