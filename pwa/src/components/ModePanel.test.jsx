import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModePanel } from './ModePanel.jsx';
import { useStore } from '../store/useStore.js';

beforeEach(() => {
  useStore.setState({ bridgeUrl: 'http://localhost:5000', mode: 'auto' });
  global.fetch = vi.fn().mockResolvedValue({ ok: true, json: () => Promise.resolve({ mode: 'auto' }) });
});

describe('ModePanel', () => {
  it('renders Auto and all 5 preset buttons', () => {
    render(<ModePanel />);
    expect(screen.getByText('Auto')).toBeInTheDocument();
    ['Club', 'Lounge', 'Party', 'Chill', 'Concert'].forEach((p) => expect(screen.getByText(p)).toBeInTheDocument());
  });

  it('Auto button has active styling when mode is auto', () => {
    render(<ModePanel />);
    expect(screen.getByText('Auto').className).toContain('purple');
  });

  it('clicking Club calls POST /mode with preset:club and updates store', async () => {
    global.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve({ mode: 'preset:club' }) });
    render(<ModePanel />);
    fireEvent.click(screen.getByText('Club'));
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(JSON.parse(global.fetch.mock.calls[0][1].body).mode).toBe('preset:club');
    expect(useStore.getState().mode).toBe('preset:club');
  });

  it('clicking Auto calls POST /mode with auto', async () => {
    useStore.setState({ mode: 'preset:club' });
    render(<ModePanel />);
    fireEvent.click(screen.getByText('Auto'));
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(JSON.parse(global.fetch.mock.calls[0][1].body).mode).toBe('auto');
  });
});
