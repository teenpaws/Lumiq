import pytest
from unittest.mock import MagicMock, patch
from bridge.lights.controller import LightController
from bridge.lights.types import Device, Command
import time

@pytest.fixture
def device():
    return Device(id="b1", tuya_id="tid1", local_key="lk1", address="192.168.1.10",
                  type="color_bulb", x=1.0, y=0.5, zone="fl",
                  latency_ms=40, online=True, capabilities=["rgb"])

def test_send_command_calls_tuya(device, mocker):
    mock_bulb = MagicMock()
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)
    ctrl = LightController([device])
    cmd = Command(device_id="b1", hex_color="#ff0000", brightness_pct=80,
                  at_timestamp=time.time())
    ctrl.send_command(cmd)
    mock_bulb.set_colour.assert_called_once_with(255, 0, 0)
    mock_bulb.set_brightness_percentage.assert_called_once_with(80)

def test_send_command_unknown_device_logs_and_skips(device, mocker):
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=MagicMock())
    ctrl = LightController([device])
    cmd = Command(device_id="unknown", hex_color="#ffffff", brightness_pct=100,
                  at_timestamp=time.time())
    ctrl.send_command(cmd)  # should not raise

def test_blink_sends_two_commands(device, mocker):
    mock_bulb = MagicMock()
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)
    mocker.patch("bridge.lights.controller.time.sleep")
    ctrl = LightController([device])
    ctrl.blink("b1")
    assert mock_bulb.turn_off.call_count == 1
    assert mock_bulb.turn_on.call_count == 1

def test_measure_latency_returns_ms(device, mocker):
    mock_bulb = MagicMock()
    mock_bulb.status.return_value = {"dps": {"20": True}}
    mocker.patch("bridge.lights.controller.tinytuya.BulbDevice", return_value=mock_bulb)
    ctrl = LightController([device])
    latency = ctrl.measure_latency("b1")
    assert isinstance(latency, int)
    assert 0 <= latency <= 5000
