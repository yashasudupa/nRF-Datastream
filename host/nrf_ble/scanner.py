# scan_ble.py
import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning for 10 seconds…")
    devs = await BleakScanner.discover(timeout=10.0)
    for d in devs:
        print(f"{d.name or '(no name)'}\t{d.address}")

if __name__ == "__main__":
    import sys
    if sys.platform.startswith("win"):
        import asyncio
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
