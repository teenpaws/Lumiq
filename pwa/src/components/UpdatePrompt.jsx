import { useRegisterSW } from 'virtual:pwa-register/react';

export function UpdatePrompt() {
  const { needRefresh: [needRefresh], updateServiceWorker } = useRegisterSW();
  if (!needRefresh) return null;
  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-purple-700 text-white text-sm px-4 py-2 flex justify-between items-center">
      <span>New version available</span>
      <button onClick={() => updateServiceWorker(true)} className="underline font-medium">Update</button>
    </div>
  );
}
