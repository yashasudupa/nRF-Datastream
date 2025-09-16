# Firmware (nRF54L15 DK)

Board: `nrf54l15dk/nrf54l15`. You can also emulate 54L10 or 54L05 with
`nrf54l15dk/nrf54l10` or `nrf54l15dk/nrf54l05` targets.

## Build & flash

```bash
# Zephyr/NCS environment initialized already
cd firmware
west build -b nrf54l15dk/nrf54l15 . -p
west flash
