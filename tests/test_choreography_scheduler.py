import time
from bridge.choreography.scheduler import BeatScheduler
from bridge.lights.types import Command

def test_scheduler_executes_due_commands():
    executed = []
    def fake_send(cmd):
        executed.append(cmd)

    scheduler = BeatScheduler(send_fn=fake_send)
    now = time.time()
    cmds = [
        Command(device_id="b1", hex_color="#ff0000", brightness_pct=80,
                at_timestamp=now + 0.05),
        Command(device_id="b2", hex_color="#0000ff", brightness_pct=60,
                at_timestamp=now + 0.10),
    ]
    scheduler.schedule(cmds)
    time.sleep(0.25)
    scheduler.stop()
    assert len(executed) == 2

def test_scheduler_executes_in_time_order():
    order = []
    def fake_send(cmd):
        order.append(cmd.device_id)

    scheduler = BeatScheduler(send_fn=fake_send)
    now = time.time()
    cmds = [
        Command(device_id="second", hex_color="#ffffff", brightness_pct=50,
                at_timestamp=now + 0.12),
        Command(device_id="first", hex_color="#ffffff", brightness_pct=50,
                at_timestamp=now + 0.05),
    ]
    scheduler.schedule(cmds)
    time.sleep(0.25)
    scheduler.stop()
    assert order == ["first", "second"]

def test_clear_removes_pending_commands():
    executed = []
    def fake_send(cmd):
        executed.append(cmd)

    scheduler = BeatScheduler(send_fn=fake_send)
    now = time.time()
    cmds = [Command(device_id="b1", hex_color="#ff0000", brightness_pct=80,
                    at_timestamp=now + 1.0)]  # 1 second in future
    scheduler.schedule(cmds)
    scheduler.clear()
    time.sleep(0.1)
    scheduler.stop()
    assert executed == []
