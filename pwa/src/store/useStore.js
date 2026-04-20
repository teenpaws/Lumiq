import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useStore = create(
  persist(
    (set) => ({
      // Persisted across sessions
      bridgeUrl: '',
      accessToken: null,
      refreshToken: null,
      expiresAt: null,

      // Ephemeral UI state
      status: 'idle',       // 'idle' | 'connected' | 'degraded' | 'partial' | 'error'
      mode: 'auto',
      currentTrack: null,
      activeProfile: null,
      musicTier: null,
      offlineDevices: null,
      bridgeError: null,
      lastHealth: null,

      setBridgeUrl: (url) => set({ bridgeUrl: url }),
      setTokens: ({ accessToken, refreshToken, expiresAt }) => set({ accessToken, refreshToken, expiresAt }),
      setMode: (mode) => set({ mode }),
      setCurrentTrack: (track) => set({ currentTrack: track }),
      setStatus: (status, extra = {}) => set({ status, ...extra }),
      clearAuth: () => set({ accessToken: null, refreshToken: null, expiresAt: null }),
    }),
    {
      name: 'lumiq-store',
      partialize: (s) => ({ bridgeUrl: s.bridgeUrl, accessToken: s.accessToken, refreshToken: s.refreshToken, expiresAt: s.expiresAt }),
    }
  )
);
