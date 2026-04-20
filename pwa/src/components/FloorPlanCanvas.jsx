const W = 320;
const H = 240;

export function FloorPlanCanvas({ floorPlan, devices, pendingDevice, onPlaceDevice }) {
  function handleClick(e) {
    if (!pendingDevice) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const x = parseFloat(((e.clientX - rect.left) / W * floorPlan.width_m).toFixed(2));
    const y = parseFloat(((e.clientY - rect.top)  / H * floorPlan.length_m).toFixed(2));
    onPlaceDevice(x, y);
  }

  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} onClick={handleClick}
      className={`bg-zinc-900 rounded-lg border border-zinc-700 ${pendingDevice ? 'cursor-crosshair' : 'cursor-default'}`}>
      <rect x={2} y={2} width={W - 4} height={H - 4} fill="none" stroke="#52525b" strokeWidth={2} />
      {devices.map((d) => {
        const cx = (d.x / floorPlan.width_m) * W;
        const cy = (d.y / floorPlan.length_m) * H;
        return (
          <g key={d.id}>
            <circle cx={cx} cy={cy} r={10} fill={d.online ? '#7c3aed' : '#7f1d1d'} opacity={0.85} />
            <text x={cx} y={cy + 20} textAnchor="middle" fill="#e4e4e7" fontSize={10}>{d.id}</text>
          </g>
        );
      })}
      {pendingDevice && <text x={W / 2} y={H - 8} textAnchor="middle" fill="#71717a" fontSize={11}>Tap to place {pendingDevice}</text>}
    </svg>
  );
}
