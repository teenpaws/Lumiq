import { vi } from 'vitest';
export const useRegisterSW = vi.fn(() => ({
  needRefresh: [false],
  offlineReady: [false],
  updateServiceWorker: vi.fn(),
}));
