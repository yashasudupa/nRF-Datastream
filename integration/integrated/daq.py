import asyncio
import struct
from bleak import BleakScanner, BleakClient

# UUIDs must match Arduino sketch
SERVICE_UUID   = "19B10000-E8F2-537E-4F6C-D104768A1214"
CHAR_UUID      = "19B10001-E8F2-537E-4F6C-D104768A1214"  # notify + write

# Commands
CMD_START = b"start_r"
CMD_STOP  = b"stop_r"
CMD_PULL  = b"get_data10_bin"

def notification_handler(sender, data: bytearray):
    """Callback whenever SmartBall notifies data."""
    try:
        txt = data.decode("utf-8")
        print(f"[text] {txt}")
    except UnicodeDecodeError:
        print(f"[bin ] {data.hex()}")

async def main():
    print("🔍 Scanning for SmartBall...")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: d.name and "SmartBall" in d.name
    )
    if not device:
        print("❌ SmartBall not found")
        return
    print(f"✅ Found SmartBall at {device.address}")

    async with BleakClient(device) as client:
        print("🔗 Connected")

        # Subscribe to notifications
        await client.start_notify(CHAR_UUID, notification_handler)

        # Send start command
        print("▶ Sending start_r")
        await client.write_gatt_char(CHAR_UUID, CMD_START)

        # Collect for ~5s
        await asyncio.sleep(5)

        # Stop recording
        print("⏹ Sending stop_r")
        await client.write_gatt_char(CHAR_UUID, CMD_STOP)
        await asyncio.sleep(1)

        # Pull buffered data
        print("📥 Pulling data...")
        await client.write_gatt_char(CHAR_UUID, CMD_PULL)

        # Allow time for all bursts
        await asyncio.sleep(3)

        await client.stop_notify(CHAR_UUID)
        print("🔚 Done.")

if __name__ == "__main__":
    asyncio.run(main())
