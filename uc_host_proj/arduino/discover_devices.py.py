from bleak import BleakScanner, BleakClient
import asyncio

async def scan_and_get_characteristics():
    print("Scanning for BLE devices...\n")
    devices = await BleakScanner.discover()

    if not devices:
        print("No BLE devices found.")
        return

    for i, d in enumerate(devices):
        print(f"[{i}] {d.name or 'Unknown'} | Address: {d.address}")

    # Let user choose a device
    index = int(input("\nEnter the index of the device to connect to: "))
    selected_device = devices[index]
    print(f"\nConnecting to {selected_device.name or 'Unknown'} ({selected_device.address})...\n")

    async with BleakClient(selected_device.address) as client:
        services = await client.get_services()
        for service in services:
            print(f"Service: {service.uuid}")
            for char in service.characteristics:
                print(f"Characteristic: {char.uuid}, Properties: {char.properties}")

asyncio.run(scan_and_get_characteristics())
