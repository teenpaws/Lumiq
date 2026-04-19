import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { DeviceCard } from './DeviceCard.jsx';
import { useStore } from '../store/useStore.js';

const DEV = { id: 'bulb_01', zone: 'front_left', latency_ms: 42, online: true };
const DEV_OFFLINE = { id: 'bulb_02', zone: 'back_right', latency_ms: null, online: false };

beforeEach(() => {
  useStore.setState({ bridgeUrl: 'http://localhost:5000' });
  global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ blinked: 'bulb_01' }) });
});

describe('DeviceCard', () => {
  it('shows device id, zone, latency, and online status', () => {
    render(<DeviceCard device={DEV} />);
    expect(screen.getByText('bulb_01')).toBeInTheDocument();
    expect(screen.getByText(/front_left/)).toBeInTheDocument();
    expect(screen.getByText(/42ms/)).toBeInTheDocument();
    expect(screen.getByText('online')).toBeInTheDocument();
  });

  it('shows "uncalibrated" when latency_ms is null', () => {
    render(<DeviceCard device={DEV_OFFLINE} />);
    expect(screen.getByText(/uncalibrated/)).toBeInTheDocument();
    expect(screen.getByText('offline')).toBeInTheDocument();
  });

  it('clicking Blink calls POST /room/blink/:id and fires onBlinked callback', async () => {
    const onBlinked = vi.fn();
    render(<DeviceCard device={DEV} onBlinked={onBlinked} />);
    fireEvent.click(screen.getByText('Blink'));
    await waitFor(() => expect(onBlinked).toHaveBeenCalledWith('bulb_01'));
    expect(global.fetch.mock.calls[0][0]).toContain('/room/blink/bulb_01');
  });
});
