import asyncio, json, sys, time
from typing import Optional
from bleak import BleakClient, BleakScanner
from . import uuids
from .parser import parse_packet, to_json
from rich.console import Console

console = Console()

async def _find_device(name: Optional[str], address: Optional[str]):
    if address:
        return address
    console.log("[bold]Scanning...[/bold]")
    devs = await BleakScanner.discover(timeout=5.0)
    for d in devs:
        if name and d.name == name:
            return d.address
    raise RuntimeError("Device not found")

async def run(name: Optional[str], address: Optional[str], save: Optional[str], once: bool):
    addr = await _find_device(name, address)
    console.log(f"Connecting to [cyan]{addr}[/cyan] ...")
    async with BleakClient(addr) as client:
        await client.start_notify(uuids.NRF_TX_CHAR, lambda h, data: None)  # prime
        logf = open(save, "a", buffering=1) if save else None

        def on_notify(_, data: bytes):
            pkt = parse_packet(data)
            if not pkt: return
            obj = to_json(pkt)
            line = json.dumps({"ts": time.time(), **obj})
            console.log(line)
            if logf: print(line, file=logf)

        await client.start_notify(uuids.NRF_TX_CHAR, on_notify)

        # send one command to get a sample
        await client.write_gatt_char(uuids.NRF_RX_CHAR, bytes([0x01]), response=False)
        if once:
            await asyncio.sleep(2.0)
        else:
            while True:
                await asyncio.sleep(1.0)

        if logf:
            logf.close()

def connect_and_log(name=None, address=None, save=None, once=False):
    asyncio.run(run(name, address, save, once))
