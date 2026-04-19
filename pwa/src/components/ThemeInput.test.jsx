import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeInput } from './ThemeInput.jsx';
import { useStore } from '../store/useStore.js';

beforeEach(() => {
  useStore.setState({ bridgeUrl: 'http://localhost:5000', mode: 'auto' });
  global.fetch = vi.fn()
    .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({ profile: { profile_name: 'tokyo_rain', mood_tag: 'calm' }, slug: 'tokyo_rain', cached: false }) })
    .mockResolvedValue({ ok: true, json: () => Promise.resolve({ mode: 'theme:tokyo_rain' }) });
});

describe('ThemeInput', () => {
  it('shows error when prompt is less than 3 chars', async () => {
    render(<ThemeInput />);
    const textarea = screen.getByPlaceholderText(/Describe a vibe/);
    await userEvent.type(textarea, 'ab');
    fireEvent.submit(textarea.closest('form'));
    expect(screen.getByText(/3–200 characters/)).toBeInTheDocument();
    expect(global.fetch).not.toHaveBeenCalled();
  });

  it('calls POST /theme then POST /mode on valid submit', async () => {
    const onApplied = vi.fn();
    render(<ThemeInput onThemeApplied={onApplied} />);
    const textarea = screen.getByPlaceholderText(/Describe a vibe/);
    await userEvent.type(textarea, 'late night Tokyo rain');
    fireEvent.submit(textarea.closest('form'));
    await waitFor(() => expect(onApplied).toHaveBeenCalled());
    expect(global.fetch.mock.calls[0][0]).toContain('/theme');
    expect(global.fetch.mock.calls[1][0]).toContain('/mode');
    expect(useStore.getState().mode).toBe('theme:tokyo_rain');
  });

  it('shows character count', async () => {
    render(<ThemeInput />);
    const textarea = screen.getByPlaceholderText(/Describe a vibe/);
    await userEvent.type(textarea, 'abc');
    expect(screen.getByText('3/200')).toBeInTheDocument();
  });

  it('disables submit button while loading', async () => {
    let resolve;
    global.fetch = vi.fn().mockReturnValue(new Promise((r) => { resolve = r; }));
    render(<ThemeInput />);
    const textarea = screen.getByPlaceholderText(/Describe a vibe/);
    await userEvent.type(textarea, 'valid prompt text');
    fireEvent.submit(textarea.closest('form'));
    expect(screen.getByText('Generating…').closest('button')).toBeDisabled();
    resolve({ ok: true, json: () => Promise.resolve({ profile: {}, slug: 's', cached: false }) });
  });
});
