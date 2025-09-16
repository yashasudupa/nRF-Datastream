#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/sensor.h>
#include "imu_lsm6dsv32x.h"

static const struct device *imu_dev;

int imu_init(void)
{
    imu_dev = DEVICE_DT_GET_ANY(st_lsm6dsv32x);
    if (!imu_dev) {
        printk("LSM6DSV32X device not found\n");
        return -ENODEV;
    }
    if (!device_is_ready(imu_dev)) {
        printk("LSM6DSV32X not ready\n");
        return -EIO;
    }
    return 0;
}

int imu_read_raw(int16_t *ax, int16_t *ay, int16_t *az,
                 int16_t *gx, int16_t *gy, int16_t *gz)
{
    if (!imu_dev) return -ENODEV;

    struct sensor_value acc[3], gyr[3];
    int ret = sensor_sample_fetch(imu_dev);
    if (ret) return ret;

    ret = sensor_channel_get(imu_dev, SENSOR_CHAN_ACCEL_XYZ, acc);
    if (ret) return ret;
    ret = sensor_channel_get(imu_dev, SENSOR_CHAN_GYRO_XYZ, gyr);
    if (ret) return ret;

    *ax = (int16_t)(sensor_value_to_double(&acc[0]) * 1000); // m/s² * 1000
    *ay = (int16_t)(sensor_value_to_double(&acc[1]) * 1000);
    *az = (int16_t)(sensor_value_to_double(&acc[2]) * 1000);
    *gx = (int16_t)(sensor_value_to_double(&gyr[0]) * 1000); // rad/s * 1000
    *gy = (int16_t)(sensor_value_to_double(&gyr[1]) * 1000);
    *gz = (int16_t)(sensor_value_to_double(&gyr[2]) * 1000);

    return 0;
}
