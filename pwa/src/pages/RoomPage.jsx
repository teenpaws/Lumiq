import { useState, useEffect } from 'react';
import { useStore } from '../store/useStore.js';
import { createClient } from '../api/bridge.js';
import { FloorPlanCanvas } from '../components/FloorPlanCanvas.jsx';
import { DeviceCard } from '../components/DeviceCard.jsx';

export function RoomPage() {
  const bridgeUrl = useStore((s) => s.bridgeUrl);
  const [floorPlan, setFloorPlan] = useState({ width_m: 4.0, length_m: 3.0 });
  const [devices, setDevices] = useState([]);
  const [calibrating, setCalibrating] = useState(false);
  const [calibrationResults, setCalibrationResults] = useState(null);

  useEffect(() => {
    if (!bridgeUrl) return;
    createClient(bridgeUrl).getRoom()
      .then(({ floor_plan, devices: devs }) => { setFloorPlan(floor_plan); setDevices(devs); })
      .catch(() => {});
  }, [bridgeUrl]);

  async function handleCalibrate() {
    setCalibrating(true);
    try {
      const { latencies_ms } = await createClient(bridgeUrl).calibrate();
      setCalibrationResults(latencies_ms);
      const { devices: updated } = await createClient(bridgeUrl).getRoom();
      setDevices(updated);
    } finally {
      setCalibrating(false);
    }
  }

  async function handleSave() {
    await createClient(bridgeUrl).saveRoom(floorPlan, devices);
  }

  return (
    <div className="p-4 space-y-4 pb-16 min-h-screen bg-zinc-950">
      <h1 className="text-lg font-semibold text-zinc-100">Room Setup</h1>
      <div className="space-y-1">
        <p className="text-xs text-zinc-500">Floor plan ({floorPlan.width_m}m × {floorPlan.length_m}m)</p>
        <FloorPlanCanvas floorPlan={floorPlan} devices={devices} pendingDevice={null} onPlaceDevice={() => {}} />
      </div>
      <div className="space-y-2">
        {devices.length === 0 && <p className="text-sm text-zinc-500">No devices in room profile yet.</p>}
        {devices.map((d) => (
          <DeviceCard key={d.id} device={d} onBlinked={() => {}} />
        ))}
      </div>
      <button onClick={handleCalibrate} disabled={calibrating || devices.length === 0}
        className="w-full py-2 rounded-lg bg-zinc-800 text-zinc-100 text-sm font-medium disabled:opacity-50">
        {calibrating ? 'Calibrating…' : 'Calibrate Latency'}
      </button>
      {calibrationResults && (
        <div className="text-xs text-zinc-400 space-y-0.5">
          {Object.entries(calibrationResults).map(([id, ms]) => <p key={id}>{id}: {ms}ms</p>)}
        </div>
      )}
      <button onClick={handleSave} className="w-full py-2 rounded-lg bg-purple-600 text-white text-sm font-medium">
        Save Room
      </button>
    </div>
  );
}
