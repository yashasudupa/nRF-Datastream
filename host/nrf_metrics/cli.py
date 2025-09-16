import argparse
from .client import connect_and_log

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--name", help="BLE name", default="NRF-BLE-DEMO")
    p.add_argument("--address", help="BLE MAC/address")
    p.add_argument("--save", help="JSONL output file")
    p.add_argument("--once", action="store_true", help="Exit after first exchange")
    args = p.parse_args()
    connect_and_log(args.name, args.address, args.save, args.once)
