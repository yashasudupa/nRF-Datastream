#pragma once
#include <stdint.h>

int imu_init(void);
int imu_read_raw(int16_t *ax, int16_t *ay, int16_t *az,
                 int16_t *gx, int16_t *gy, int16_t *gz);
