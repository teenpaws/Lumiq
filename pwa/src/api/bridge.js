export function createClient(bridgeUrl) {
  const base = bridgeUrl.replace(/\/$/, '');

  async function req(method, path, body) {
    const opts = { method, signal: AbortSignal.timeout(5000) };
    opts.headers = { 'ngrok-skip-browser-warning': '1' };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(`${base}${path}`, opts);
    if (!res.ok) throw new Error(`Bridge ${method} ${path} → ${res.status}`);
    return res.json();
  }

  return {
    getHealth:     ()                                          => req('GET',  '/health'),
    getMode:       ()                                          => req('GET',  '/mode'),
    setMode:       (mode)                                      => req('POST', '/mode',             { mode }),
    pushTrack:     (track_id, position_ms, is_playing, access_token) =>
                                                                  req('POST', '/track',            { track_id, position_ms, is_playing, access_token }),
    generateTheme: (prompt)                                    => req('POST', '/theme',            { prompt }),
    getRoom:       ()                                          => req('GET',  '/room'),
    saveRoom:      (floor_plan, devices)                       => req('POST', '/room',             { floor_plan, devices }),
    blinkDevice:   (device_id)                                 => req('POST', `/room/blink/${device_id}`),
    calibrate:     ()                                          => req('POST', '/room/calibrate'),
    listRooms:     ()                                          => req('GET',  '/rooms'),
    saveNamedRoom: (name)                                      => req('POST', `/rooms/${encodeURIComponent(name)}/save`),
    loadNamedRoom: (name)                                      => req('POST', `/rooms/${encodeURIComponent(name)}/load`),
  };
}
