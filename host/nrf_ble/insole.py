# insole.py
import asyncio
import time
import struct
import threading
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Any

from bleak import BleakClient, BleakScanner

from .json_writer import JSONLinesWriter
from .config import (
    LEFT_NAME, RIGHT_NAME,
    SERVICE_UUID, CMD_CHAR_UUID, DATA_CHAR_UUID,
    CMD_START, CMD_STOP, CMD_PULL,
    CHANNEL_LABELS, AREA_CM2, DEV_TS_UNITS_PER_S
)

# =========================== Data Structures ===========================

@dataclass
class DeviceState:
    side: str
    expected_bytes: int = 0
    recv_buf: bytearray = field(default_factory=bytearray)
    last_batch: List[Tuple[int, Tuple[int, ...]]] = field(default_factory=list)
    batch_ready: threading.Event = field(default_factory=threading.Event)
    done_event: threading.Event = field(default_factory=threading.Event)
    # Analytics buffers (per side)
    times_s: List[float] = field(default_factory=list)                 # device time (s)
    forces_by_label: List[Dict[str, float]] = field(default_factory=list)  # {"label": force_N, ...}
    # NEW: per-sample sensor objects (time-aligned)
    # each item: {"t": float, "sensors": [{"label","analog","resistance","force","pressure"}, ...]}
    sensors: List[Dict[str, Any]] = field(default_factory=list)

# =========================== Calibration & Math ===========================

def calibrate(analog_val: int):
    """
    Convert raw ADC to (resistance_ohm, force_newtons). Clamp force to [0, 30].
    NOTE: Uses the same formula you shared; tweak if you later re-calibrate.
    """
    if analog_val >= 4095 or analog_val == 0:
        return 0.0, 0.0
    try:
        # Example mapping (placeholder R-curve): adjust to your divider exactly if needed.
        resistance = (analog_val / (4095 - analog_val)) * 3.3
        force = 156.6869 * (resistance ** -1.839)
        return resistance, min(max(force, 0.0), 30.0)
    except Exception:
        return 0.0, 0.0

def force_to_pressure(force_newtons: float, label: str) -> float:
    """
    Convert force (N) to pressure (Pa) using area from AREA_CM2 per label.
    """
    area_m2 = (AREA_CM2.get(label, 6.5)) * 1e-4  # default 6.5 cm^2 if missing
    return (force_newtons / area_m2) if area_m2 > 0 else 0.0

# =========================== Parsing & Accumulation ===========================

def parse_samples(buf: bytes, count: int) -> List[Tuple[int, Tuple[int, ...]]]:
    """
    Parse count samples of little-endian frames: <I8H> = (uint32 timestamp, 8*uint16 channels).
    Each frame is 20 bytes.
    Returns: list of (dev_ts, (v0..v7))
    """
    out, off = [], 0
    for _ in range(count):
        ts, *vals = struct.unpack_from("<I8H", buf, off)  # 4B + 8*2B = 20B
        out.append((ts, tuple(vals)))
        off += 20
    return out

def sample_to_insole_object(vals: Tuple[int, ...]) -> dict:
    """
    Build per-sample JSON-friendly structure with derived metrics per sensor channel.
    Returns: {"sensors": [ {label, analog, resistance, force, pressure}, ... ]}
    """
    sensors = []
    for i, label in enumerate(CHANNEL_LABELS):
        analog = int(vals[i])
        resistance, force = calibrate(analog)
        pressure = force_to_pressure(force, label) if force > 0 else 0.0
        sensors.append({
            "label": label,
            "analog": analog,
            "resistance": resistance,
            "force": force,
            "pressure": pressure
        })
    return {"sensors": sensors}

def _accumulate_for_analysis(state: DeviceState, dev_ts: int, vals: Tuple[int, ...]):
    """
    Append lightweight arrays for plotting/analysis (time series & force-by-label).
    """
    t_s = dev_ts / DEV_TS_UNITS_PER_S
    by_label: Dict[str, float] = {}
    for i, label in enumerate(CHANNEL_LABELS):
        _, f = calibrate(int(vals[i]))
        by_label[label] = f  # in Newtons
    state.times_s.append(t_s)
    state.forces_by_label.append(by_label)

def emit_batch_json(writer: JSONLinesWriter, side: str,
                    batch: List[Tuple[int, Tuple[int, ...]]],
                    state: DeviceState):
    """
    For each parsed sample in the batch:
      - stream a JSON line to writer
      - update analysis buffers (times_s, forces_by_label)
      - NEW: store full per-sample sensors object (with time) into state.sensors
    """
    host_ts = time.time()
    side_key = "left_insole" if side.startswith("left") else "right_insole"

    for dev_ts, vals in batch:
        # Build per-sample object
        ins = sample_to_insole_object(vals)

        # Stream JSON line
        rec = {"timestamp": host_ts, "left_insole": None, "right_insole": None}
        rec[side_key] = ins
        writer.append(rec)

        # Accumulate analytics
        _accumulate_for_analysis(state, dev_ts, vals)

        # Keep the detailed sensors object with device time
        t_s = dev_ts / DEV_TS_UNITS_PER_S
        state.sensors.append({"t": t_s, "sensors": ins["sensors"]})

# =========================== Notification Handler ===========================

def make_notify_handler(state: DeviceState):
    """
    Handles three textual control markers sent by peripheral:
      - "BIN10:<n>" -> expect n*20 bytes of binary payload (<I8H frames)
      - "BATCH_DONE" -> parse accumulated bytes into frames
      - "Done" -> end of session
    Otherwise treats incoming data as raw binary belonging to the current batch.
    """
    def handler(_sender, data: bytearray):
        try:
            text = data.decode("utf-8")
            if text.startswith("BIN10:"):
                n = int(text.split(":", 1)[1])
                state.expected_bytes = n * 20
                state.recv_buf.clear()
                state.last_batch = []
                return
            if text == "BATCH_DONE":
                if state.expected_bytes and len(state.recv_buf) >= state.expected_bytes:
                    cnt = state.expected_bytes // 20
                    state.last_batch = parse_samples(state.recv_buf[:state.expected_bytes], cnt)
                state.batch_ready.set()
                return
            if text == "Done":
                state.done_event.set()
                state.batch_ready.set()
                return
        except UnicodeDecodeError:
            # binary chunk
            pass
        # Append raw binary to the receive buffer
        state.recv_buf.extend(data)
    return handler

# =========================== Pull Worker (host-driven pulls) ===========================

class PullWorker(threading.Thread):
    """
    Background thread that periodically sends CMD_PULL to fetch the next batch.
    It waits on state.batch_ready which is signaled by the notify handler when a batch completes.
    """
    def __init__(self, side: str, client: BleakClient, loop: asyncio.AbstractEventLoop,
                 state: DeviceState, writer: JSONLinesWriter):
        super().__init__(daemon=True)
        self.side = side
        self.client = client
        self.loop = loop
        self.state = state
        self.writer = writer

    def run(self):
        while not self.state.done_event.is_set():
            self.state.batch_ready.clear()

            # Ask the peripheral to send the next batch
            fut = asyncio.run_coroutine_threadsafe(
                self.client.write_gatt_char(CMD_CHAR_UUID, CMD_PULL),
                self.loop
            )
            try:
                fut.result(timeout=2.0)
            except Exception:
                time.sleep(0.05)
                continue

            # Wait until we either got the batch, or timeout to try again
            if not self.state.batch_ready.wait(timeout=5.0):
                continue

            if self.state.done_event.is_set():
                break

            if self.state.last_batch:
                emit_batch_json(self.writer, self.side, self.state.last_batch, self.state)

# =========================== BLE Helpers ===========================

async def find_and_connect(name_substr: str, state: DeviceState) -> BleakClient:
    """
    Scan for a device whose name contains `name_substr`, connect, and enable notifications.
    """
    print(f"[SCAN] Looking for '{name_substr}'...")
    dev = await BleakScanner.find_device_by_filter(
        lambda d, ad: (d.name is not None) and (name_substr in d.name)
    )
    if not dev:
        raise RuntimeError(f"Device '{name_substr}' not found")
    print(f"[SCAN] Found: {dev.name} ({dev.address})")

    client = BleakClient(dev)
    await client.connect()
    print(f"[BLE] Connected to {name_substr}")

    await client.start_notify(DATA_CHAR_UUID, make_notify_handler(state))
    print(f"[BLE] Notifications enabled for {name_substr}")
    return client

# =========================== Orchestration ===========================

async def run_insoles(writer: JSONLinesWriter, stop_event: asyncio.Event | None = None):
    """
    Connect to left insole, start pull worker, start/stop recording, wait for 'Done',
    clean up, and return analysis buffers + full per-sample sensor objects.
    """
    # Connect (sequence)
    left_state = DeviceState("left_insole")
    # right_state = DeviceState("right_insole")  # enable when you wire the right foot
    left_client = await find_and_connect(LEFT_NAME, left_state)
    # right_client = await find_and_connect(RIGHT_NAME, right_state)

    loop = asyncio.get_running_loop()

    # Start pullers (parallel)
    left_worker = PullWorker("left_insole", left_client, loop, left_state, writer)
    # right_worker = PullWorker("right_insole", right_client, loop, right_state, writer)
    left_worker.start()
    # right_worker.start()

    # Start/Stop (sequence)
    print("[ACTION] start_r left")
    await left_client.write_gatt_char(CMD_CHAR_UUID, CMD_START)
    await asyncio.sleep(0.1)

    # print("[ACTION] start_r right")
    # await right_client.write_gatt_char(CMD_CHAR_UUID, CMD_START)

    # Wait for external stop, or fall back to input if none given
    if stop_event is not None:
        await stop_event.wait()
    else:
        input("Recording (insoles). Press ENTER here to stop insoles.\n")

    print("[ACTION] stop_r left")
    await left_client.write_gatt_char(CMD_CHAR_UUID, CMD_STOP)
    await asyncio.sleep(0.2)

    # print("[ACTION] stop_r right")
    # await right_client.write_gatt_char(CMD_CHAR_UUID, CMD_STOP)

    # Wait & cleanup
    print("[WAIT] Waiting for 'Done' from both insoles...")
    t0 = time.time()
    while not left_state.done_event.is_set():
        await asyncio.sleep(0.1)
        if time.time() - t0 > 120:
            print("[WARN] Timeout waiting; proceeding.")
            break

    try:
        await left_client.stop_notify(DATA_CHAR_UUID)
        # await right_client.stop_notify(DATA_CHAR_UUID)
    finally:
        await left_client.disconnect()
        # await right_client.disconnect()

    # Return analysis buffers + per-sample sensors for each foot (left only for now)
    return {
        "left": {
            "t": left_state.times_s,
            "forces_by_label": left_state.forces_by_label,
            # list of {"t": float, "sensors":[{"label","analog","resistance","force","pressure"}]}
            "sensors": left_state.sensors
        }
        # "right": {
        #     "t": right_state.times_s,
        #     "forces_by_label": right_state.forces_by_label,
        #     "sensors": right_state.sensors
        # }
    }
