import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBanner } from './StatusBanner.jsx';
import { useStore } from '../store/useStore.js';

beforeEach(() => useStore.setState({ status: 'idle', musicTier: null, offlineDevices: null, bridgeError: null }));

describe('StatusBanner', () => {
  it('shows "Connecting…" when idle', () => {
    render(<StatusBanner />);
    expect(screen.getByText('Connecting…')).toBeInTheDocument();
  });

  it('shows "Connected" with green class when connected', () => {
    useStore.setState({ status: 'connected' });
    const { container } = render(<StatusBanner />);
    expect(screen.getByText('Connected')).toBeInTheDocument();
    expect(container.firstChild.className).toContain('green');
  });

  it('shows tier info when degraded', () => {
    useStore.setState({ status: 'degraded', musicTier: 2 });
    render(<StatusBanner />);
    expect(screen.getByText('Degraded')).toBeInTheDocument();
    expect(screen.getByText(/Music tier: 2/)).toBeInTheDocument();
  });

  it('shows offline count when partial', () => {
    useStore.setState({ status: 'partial', offlineDevices: 3 });
    render(<StatusBanner />);
    expect(screen.getByText('Some bulbs offline')).toBeInTheDocument();
    expect(screen.getByText(/3 offline/)).toBeInTheDocument();
  });

  it('shows error message when bridge unreachable', () => {
    useStore.setState({ status: 'error', bridgeError: 'Bridge unreachable' });
    render(<StatusBanner />);
    expect(screen.getByText('Bridge offline')).toBeInTheDocument();
    expect(screen.getByText(/Bridge unreachable/)).toBeInTheDocument();
  });
});
