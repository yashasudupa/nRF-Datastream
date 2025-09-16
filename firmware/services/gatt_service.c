#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>
#include "gatt_uuids.h"
#include "gatt_service.h"

static rx_handler_t rx_cb = NULL;
static bool notify_enabled = false;
static uint8_t tx_buf[200];
static ssize_t rx_write(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                        const void *buf, uint16_t len, uint16_t offset, uint8_t flags);

BT_GATT_SERVICE_DEFINE(nrf_svc,
  BT_GATT_PRIMARY_SERVICE(&BT_UUID_NRF_SVC),
  /* TX characteristic (Notify) */
  BT_GATT_CHARACTERISTIC(&BT_UUID_NRF_TX.uuid, BT_GATT_CHRC_NOTIFY,
                         BT_GATT_PERM_NONE, NULL, NULL, tx_buf),
  BT_GATT_CCC(((struct _bt_gatt_ccc[]) {{
      .cfg = NULL, .cfg_len = 0, .cfg_changed = NULL
  }}), BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),
  /* RX characteristic (Write / Write Without Response) */
  BT_GATT_CHARACTERISTIC(&BT_UUID_NRF_RX.uuid,
                         BT_GATT_CHRC_WRITE | BT_GATT_CHRC_WRITE_WITHOUT_RESP,
                         BT_GATT_PERM_WRITE, NULL, rx_write, NULL)
);

static void ccc_cfg_changed(const struct bt_gatt_attr *attr, uint16_t value)
{
  notify_enabled = (value == BT_GATT_CCC_NOTIFY);
}

static struct bt_gatt_ccc_cfg nrf_tx_ccc_cfg[BT_GATT_CCC_MAX] = {};
static struct bt_gatt_ccc nrf_tx_ccc = BT_GATT_CCC_INIT(nrf_tx_ccc_cfg, ccc_cfg_changed);

static ssize_t rx_write(struct bt_conn *conn, const struct bt_gatt_attr *attr,
                        const void *buf, uint16_t len, uint16_t offset, uint8_t flags)
{
  ARG_UNUSED(conn); ARG_UNUSED(attr); ARG_UNUSED(offset); ARG_UNUSED(flags);
  if (rx_cb) { rx_cb((const uint8_t*)buf, len); }
  return len;
}

int gatt_service_init(rx_handler_t on_rx)
{
  rx_cb = on_rx;
  /* Patch the CCC descriptor (Zephyr macro above uses a placeholder) */
  /* Find CCC attr (index 2 after TX char & value) -> safer to iterate: */
  for (size_t i = 0; i < nrf_svc.attr_count; ++i) {
    struct bt_gatt_attr *a = (struct bt_gatt_attr *)&nrf_svc.attrs[i];
    if (a->write == bt_gatt_attr_write_ccc) {
      a->user_data = &nrf_tx_ccc;
      break;
    }
  }
  return 0;
}

int gatt_send_notify(const uint8_t *data, size_t len)
{
  if (!notify_enabled) return -EACCES;
  struct bt_gatt_attr *val = (struct bt_gatt_attr *)&nrf_svc.attrs[1]; // TX value attr
  return bt_gatt_notify(NULL, val, data, len);
}
