import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SettingsPage } from './SettingsPage.jsx';
import { useStore } from '../store/useStore.js';

beforeEach(() => {
  useStore.setState({ bridgeUrl: '', accessToken: null });
  global.fetch = vi.fn();
});

describe('SettingsPage', () => {
  it('shows "Not authenticated" when no Spotify token', () => {
    render(<SettingsPage />);
    expect(screen.getByText(/Not authenticated/)).toBeInTheDocument();
  });

  it('shows "Authenticated" and sign-out button when token present', () => {
    useStore.setState({ accessToken: 'tok' });
    render(<SettingsPage />);
    expect(screen.getByText(/Authenticated/)).toBeInTheDocument();
    expect(screen.getByText('Sign out')).toBeInTheDocument();
  });

  it('sign out clears tokens', async () => {
    useStore.setState({ accessToken: 'tok', refreshToken: 'r', expiresAt: 999 });
    render(<SettingsPage />);
    fireEvent.click(screen.getByText('Sign out'));
    expect(useStore.getState().accessToken).toBeNull();
  });

  it('saves bridge URL and shows success on successful health check', async () => {
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ status: 'ok', devices_total: 2, devices_online: 2, mode: 'auto', active_profile: null, last_music_tier: 0 }) });
    render(<SettingsPage />);
    const input = screen.getByPlaceholderText(/192\.168/);
    await userEvent.clear(input);
    await userEvent.type(input, 'http://localhost:5000');
    fireEvent.click(screen.getByText('Save & Test'));
    await waitFor(() => screen.getByText(/Connected — 2 devices/));
    expect(useStore.getState().bridgeUrl).toBe('http://localhost:5000');
  });

  it('shows error when bridge is unreachable', async () => {
    global.fetch.mockRejectedValue(new Error('Failed to fetch'));
    render(<SettingsPage />);
    const input = screen.getByPlaceholderText(/192\.168/);
    await userEvent.type(input, 'http://localhost:9999');
    fireEvent.click(screen.getByText('Save & Test'));
    await waitFor(() => screen.getByText(/Could not reach bridge/));
  });
});
