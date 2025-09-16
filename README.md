# nrf_metrics

Minimal, structured nRF BLE stack:
- **firmware/**: Zephyr-based app exposing a custom GATT service with Notify + Write.
- **host/**: Python package/CLI using Bleak to connect, subscribe, parse packets, and log JSONL.
- **shared/**: Protocol docs and UUIDs.
- **tools/**: Flash helpers and quick plotting.

## Quickstart

### Firmware (Zephyr)
```bash
# One-time:
west init -m https://github.com/zephyrproject-rtos/zephyr --mr v3.7.0 zephyrproject
cd zephyrproject && west update
west zephyr-export
pip install -r zephyr/scripts/requirements.txt

# Build this app:
cd /path/to/nrf_ble/firmware
west build -b nrf52840dk/nrf52840 . -p
west flash
