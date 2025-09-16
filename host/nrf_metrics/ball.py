from .json_writer import JSONLinesWriter
from .metrics import compute_metrics
from .uuids import BALL_CMD_CHAR, BALL_DATA_CHAR
import asyncio, time, struct, math
from bleak import BleakScanner, BleakClient

# UUIDs must match Arduino sketch
SERVICE_UUID = "19B10000-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID    = "19B10001-E8F2-537E-4F6C-D104768A1214"  # notify + write

# Commands
CMD_START = b"start_r"
CMD_STOP  = b"stop_r"
CMD_PULL  = b"get_data10_bin"


class BallState:
    def __init__(self):
        self.recv = bytearray()
        self.expected_bytes = 0
        self.batch = []
        self.batch_ready = asyncio.Event()
        self.done = asyncio.Event()
        self.start_ms = None
        self.end_ms = None
        # metrics
        self.sample_count = 0
        self.sum_rev_per_sec = 0.0
        self.peak_omega_deg_s = 0.0

    def notify(self, _sender, data: bytearray):
        # timing packet
        if len(data) == 8 and self.expected_bytes == 0:
            self.start_ms, self.end_ms = struct.unpack_from("<II", data, 0)
            return
        try:
            txt = data.decode("utf-8")
            if txt.startswith("BIN10:"):
                n = int(txt.split(":", 1)[1])
                self.expected_bytes = n * 12
                self.recv.clear()
                self.batch.clear()
                return
            if txt == "BATCH_DONE":
                if self.expected_bytes and len(self.recv) >= self.expected_bytes:
                    out, off = [], 0
                    for _ in range(self.expected_bytes // 12):
                        ax, ay, az, gx, gy, gz = struct.unpack_from("<6h", self.recv, off)
                        out.append((ax, ay, az, gx, gy, gz))
                        off += 12
                    self.batch = out
                    # accumulate metrics
                    for _ax, _ay, _az, gx, gy, gz in out:
                        omega = math.sqrt(gx*gx + gy*gy + gz*gz)
                        self.peak_omega_deg_s = max(self.peak_omega_deg_s, omega)
                        self.sum_rev_per_sec += omega / 360.0
                        self.sample_count += 1
                self.batch_ready.set()
                return
            if txt == "Done":
                self.done.set()
                self.batch_ready.set()
                return
        except UnicodeDecodeError:
            pass
        # binary chunk
        self.recv.extend(data)


async def run_ball(writer: JSONLinesWriter, stop_event: asyncio.Event | None = None):
    print("🔍 Scanning for SmartBall...")
    dev = await BleakScanner.find_device_by_filter(lambda d, ad: d.name and "SmartBall" in d.name)
    if not dev:
        raise RuntimeError("❌ SmartBall not found")
    print(f"✅ Found SmartBall at {dev.address}")

    st = BallState()
    async with BleakClient(dev) as client:
        print("🔗 Connected")
        await client.start_notify(CHAR_UUID, st.notify)

        # start
        await client.write_gatt_char(CHAR_UUID, CMD_START)

        # Wait for external stop, or fall back to input if none given
        if stop_event is not None:
            await stop_event.wait()
        else:
            input("[ball] Recording... press ENTER to STOP\n")

        await client.write_gatt_char(CHAR_UUID, CMD_STOP)
        await asyncio.sleep(0.3)

        # pull loop
        while not st.done.is_set():
            st.batch_ready.clear()
            await client.write_gatt_char(CHAR_UUID, CMD_PULL)
            try:
                await asyncio.wait_for(st.batch_ready.wait(), 5.0)
            except asyncio.TimeoutError:
                continue

            if st.batch:
                # append raw records
                writer.append({
                    "timestamp": time.time(),
                    "ball": {
                        "records": [
                            {"ax": r[0], "ay": r[1], "az": r[2], "gx": r[3], "gy": r[4], "gz": r[5]}
                            for r in st.batch
                        ]
                    }
                })

        await client.stop_notify(CHAR_UUID)

    # ---- summary ----
    duration_s = 0.0
    if st.start_ms is not None and st.end_ms is not None and st.end_ms >= st.start_ms:
        duration_s = (st.end_ms - st.start_ms) / 1000.0

    if st.sample_count > 0 and duration_s > 0.0:
        avg_rev_per_sec = st.sum_rev_per_sec / st.sample_count
        total_revolutions = avg_rev_per_sec * duration_s
    else:
        avg_rev_per_sec = 0.0
        total_revolutions = 0.0

    summary = {
        "timestamp": time.time(),
        "ball_summary": {
            "t_start_ms": int(st.start_ms) if st.start_ms is not None else None,
            "t_end_ms":   int(st.end_ms) if st.end_ms is not None else None,
            "duration_s": duration_s,
            "samples": st.sample_count,
            "avg_rev_per_sec": avg_rev_per_sec,
            "avg_spin_rpm": avg_rev_per_sec * 60.0,
            "total_revolutions": total_revolutions,
            "omega_deg_s_peak": st.peak_omega_deg_s,
            "spin_rps_peak": st.peak_omega_deg_s / 360.0,
            "spin_rpm_peak": (st.peak_omega_deg_s / 360.0) * 60.0
        }
    }

    # append to file
    writer.append(summary)

    # return for main()
    return summary
