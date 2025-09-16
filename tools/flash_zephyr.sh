#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../firmware"
west build -b nrf52840dk/nrf52840 . -p
west flash
