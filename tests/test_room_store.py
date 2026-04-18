import json, os, pytest
from bridge.lights.room import RoomStore
from bridge.lights.types import Device

@pytest.fixture
def store(tmp_path):
    path = str(tmp_path / "room_profile.json")
    return RoomStore(path)

def test_empty_store_returns_no_devices(store):
    assert store.get_devices() == []

def test_save_and_reload(store, tmp_path):
    devices = [
        Device(id="b1", tuya_id="t1", local_key="k1", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    ]
    floor_plan = {"width_m": 4.2, "length_m": 3.6, "shape": "rectangle"}
    store.save(floor_plan, devices)

    store2 = RoomStore(str(tmp_path / "room_profile.json"))
    loaded = store2.get_devices()
    assert len(loaded) == 1
    assert loaded[0].id == "b1"
    assert loaded[0].latency_ms == 40

def test_update_device_latency(store):
    devices = [
        Device(id="b1", tuya_id="t1", local_key="k1", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    ]
    store.save({"width_m": 4.0, "length_m": 3.0, "shape": "rectangle"}, devices)
    store.update_device(id="b1", latency_ms=65)
    assert store.get_device("b1").latency_ms == 65

def test_mark_device_offline(store):
    devices = [
        Device(id="b1", tuya_id="t1", local_key="k1", address="192.168.1.10",
               type="color_bulb", x=1.0, y=0.5, zone="front_left",
               latency_ms=40, online=True, capabilities=["rgb"])
    ]
    store.save({"width_m": 4.0, "length_m": 3.0, "shape": "rectangle"}, devices)
    store.update_device(id="b1", online=False)
    assert store.get_device("b1").online is False
