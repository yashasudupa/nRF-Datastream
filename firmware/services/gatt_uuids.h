#pragma once
#include <zephyr/bluetooth/uuid.h>

/* Keep in sync with shared/proto/uuids.json / host/nrf_ble/uuids.py */

#define BT_UUID_NRF_SVC_VAL \
  BT_UUID_128_ENCODE(0xf0e0b000, 0x0451, 0x4000, 0xb000, 0x000000000000ULL)
#define BT_UUID_NRF_TX_VAL  \
  BT_UUID_128_ENCODE(0xf0e0b001, 0x0451, 0x4000, 0xb000, 0x000000000000ULL)
#define BT_UUID_NRF_RX_VAL  \
  BT_UUID_128_ENCODE(0xf0e0b002, 0x0451, 0x4000, 0xb000, 0x000000000000ULL)

static struct bt_uuid_128 BT_UUID_NRF_SVC = BT_UUID_INIT_128(BT_UUID_NRF_SVC_VAL);
static struct bt_uuid_128 BT_UUID_NRF_TX  = BT_UUID_INIT_128(BT_UUID_NRF_TX_VAL);
static struct bt_uuid_128 BT_UUID_NRF_RX  = BT_UUID_INIT_128(BT_UUID_NRF_RX_VAL);
