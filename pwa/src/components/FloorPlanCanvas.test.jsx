import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { FloorPlanCanvas } from './FloorPlanCanvas.jsx';

const FP = { width_m: 4.0, length_m: 3.0 };
const DEVS = [{ id: 'bulb_01', x: 2.0, y: 1.5, zone: 'center', online: true }];

describe('FloorPlanCanvas', () => {
  it('renders a circle for each device', () => {
    const { container } = render(<FloorPlanCanvas floorPlan={FP} devices={DEVS} pendingDevice={null} onPlaceDevice={() => {}} />);
    expect(container.querySelectorAll('circle').length).toBe(1);
  });

  it('renders device id label', () => {
    const { getByText } = render(<FloorPlanCanvas floorPlan={FP} devices={DEVS} pendingDevice={null} onPlaceDevice={() => {}} />);
    expect(getByText('bulb_01')).toBeInTheDocument();
  });

  it('calls onPlaceDevice with meter coords when clicked with pendingDevice set', () => {
    const onPlace = vi.fn();
    const { container } = render(<FloorPlanCanvas floorPlan={FP} devices={[]} pendingDevice="bulb_02" onPlaceDevice={onPlace} />);
    const svg = container.querySelector('svg');
    svg.getBoundingClientRect = () => ({ left: 0, top: 0 });
    fireEvent.click(svg, { clientX: 160, clientY: 120 }); // 160/320 * 4.0 = 2.0m, 120/240 * 3.0 = 1.5m
    expect(onPlace).toHaveBeenCalledWith(2.0, 1.5);
  });

  it('does not call onPlaceDevice when pendingDevice is null', () => {
    const onPlace = vi.fn();
    const { container } = render(<FloorPlanCanvas floorPlan={FP} devices={[]} pendingDevice={null} onPlaceDevice={onPlace} />);
    const svg = container.querySelector('svg');
    svg.getBoundingClientRect = () => ({ left: 0, top: 0 });
    fireEvent.click(svg, { clientX: 100, clientY: 100 });
    expect(onPlace).not.toHaveBeenCalled();
  });
});
