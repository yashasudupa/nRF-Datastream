#include <zephyr/kernel.h>
#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/hci.h>
#include <string.h>
#include "app_config.h"
#include "gatt_service.h"
#include "imu_lsm6dsv32x.h"

static void on_rx(const uint8_t *data, size_t len)
{
  /* Example: echo command 0x01 -> send one IMU sample */
  if (len >= 1 && data[0] == 0x01) {
    int16_t ax, ay, az, gx, gy, gz;
    if (imu_read_raw(&ax, &ay, &az, &gx, &gy, &gz) == 0) {
      uint8_t pkt[1 + 12];
      pkt[0] = 0x10; // sample opcode
      memcpy(&pkt[1], &ax, 2); memcpy(&pkt[3], &ay, 2); memcpy(&pkt[5], &az, 2);
      memcpy(&pkt[7], &gx, 2); memcpy(&pkt[9], &gy, 2); memcpy(&pkt[11], &gz, 2);
      gatt_send_notify(pkt, sizeof(pkt));
    }
  }
}

void main(void)
{
  int err;

  err = bt_enable(NULL);
  if (err) { return; }

  gatt_service_init(on_rx);
  imu_init();

  struct bt_le_adv_param advp = {
    .options = BT_LE_ADV_OPT_CONNECTABLE,
    .id = BT_ID_DEFAULT,
    .interval_min = BT_GAP_ADV_FAST_INT_MIN_2,
    .interval_max = BT_GAP_ADV_FAST_INT_MAX_2,
  };

  const char dev_name[] = APP_DEVICE_NAME;
  bt_le_adv_start(&advp,
    (struct bt_data []) {
      BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
      BT_DATA(BT_DATA_NAME_COMPLETE, dev_name, sizeof(dev_name) - 1)
    }, 2,
    NULL, 0);

  while (1) {
    k_sleep(K_SECONDS(1));
    /* Periodic notify demo: 0x20 heartbeat */
    uint8_t hb[2] = {0x20, 0x01};
    gatt_send_notify(hb, sizeof(hb));
  }
}
