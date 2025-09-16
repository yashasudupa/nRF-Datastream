#pragma once
#include <stddef.h>
#include <stdint.h>

typedef void (*rx_handler_t)(const uint8_t *data, size_t len);

int gatt_service_init(rx_handler_t on_rx);
int gatt_send_notify(const uint8_t *data, size_t len);
