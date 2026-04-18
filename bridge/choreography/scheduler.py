import heapq
import threading
import time
import logging
from typing import Callable, List
from bridge.lights.types import Command

logger = logging.getLogger("lumiq")

class BeatScheduler:
    def __init__(self, send_fn: Callable[[Command], None]):
        self._queue: list = []  # heapq of (at_timestamp, id(cmd), cmd)
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._send_fn = send_fn
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def schedule(self, commands: List[Command]):
        with self._lock:
            for cmd in commands:
                heapq.heappush(self._queue, (cmd.at_timestamp, id(cmd), cmd))

    def clear(self):
        with self._lock:
            self._queue.clear()

    def stop(self):
        self._stop_event.set()
        self._thread.join(timeout=1.0)

    def _run(self):
        while not self._stop_event.is_set():
            now = time.time()
            with self._lock:
                while self._queue and self._queue[0][0] <= now:
                    _, _, cmd = heapq.heappop(self._queue)
                    try:
                        self._send_fn(cmd)
                    except Exception as e:
                        logger.error("scheduler send error device=%s err=%s", cmd.device_id, e)
            time.sleep(0.005)  # 5ms tick
