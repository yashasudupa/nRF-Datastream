#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/logging/log.h>

LOG_MODULE_REGISTER(app, LOG_LEVEL_INF);

/* ---------- CONFIGURE YOUR PINS / BUS HERE ---------- */
/* I2C IMU bus + address */
#define IMU_I2C_NODE       DT_NODELABEL(i2c0)           /* adjust if different */
#define IMU_I2C_ADDR       0x6A                         /* 0x6A or 0x6B depending on SA0 */

/* IMU INT1 pin (watermark / DRDY) */
#define IMU_INT_NODE       DT_NODELABEL(gpio0)          /* change to your GPIO port */
#define IMU_INT_PIN        15                           /* <-- CHANGE to your actual INT1 pin */
#define IMU_INT_FLAGS      (GPIO_INPUT | GPIO_PULL_DOWN)

/* SAADC channel for PIEZO peak node */
#define PIEZO_ADC_NODE     DT_NODELABEL(adc0)           /* nRF54 SAADC */
#define PIEZO_ADC_CH       0                            /* logical channel index */
#define PIEZO_ADC_AIN      SAADC_CH_PSELN_PSELN_NC      /* single-ended */
#define PIEZO_ADC_PIN      NRF_SAADC_INPUT_AIN0         /* <-- CHANGE to your analog pin */

/* Poll rate for piezo peak detection (Hz) */
#define PIEZO_POLL_HZ      1000
#define PIEZO_THR_MV       800    /* threshold in mV (tune) */
#define PIEZO_HYS_MV       120    /* hysteresis */

/* IMU ODR (acc+gyro) */
#define IMU_ODR_HZ         104

/* ---------- LSM6DSV32x REG MAP (verify on your exact part!) ---------- */
enum {
    REG_FUNC_CFG_ACCESS   = 0x01,
    REG_FIFO_CTRL1        = 0x07,
    REG_FIFO_CTRL2        = 0x08,
    REG_FIFO_CTRL3        = 0x09,
    REG_FIFO_CTRL4        = 0x0A,
    REG_INT1_CTRL         = 0x0D,
    REG_WHO_AM_I          = 0x0F,
    REG_CTRL1_XL          = 0x10,
    REG_CTRL2_G           = 0x11,
    REG_CTRL3_C           = 0x12,
    REG_STATUS_REG        = 0x1E,
    REG_OUTX_L_G          = 0x22,
    REG_OUTX_L_A          = 0x28,
    REG_FIFO_STATUS1      = 0x3A,
    REG_FIFO_STATUS2      = 0x3B,
    REG_FIFO_DATA_OUT_TAG = 0x78,  /* family uses tagged FIFO; some variants use 0x3E */
    REG_FIFO_DATA_OUT_X_L = 0x3E
};

/* CTRL codes (simplified) */
static uint8_t odr_xl_code(uint16_t hz) {
    /* 12.5=0x10, 26=0x20, 52=0x30, 104=0x40, 208=0x50, 416=0x60 ... */
    if (hz >= 416) return 0x60;
    if (hz >= 208) return 0x50;
    if (hz >= 104) return 0x40;
    if (hz >=  52) return 0x30;
    if (hz >=  26) return 0x20;
    return 0x10;
}
static uint8_t fs_xl_code(uint16_t g) {
    /* 2g=0x00, 4g=0x08, 8g=0x0C, 16g=0x04, (32g depends on x32 variant) */
    if (g >= 16) return 0x04;
    if (g >=  8) return 0x0C;
    if (g >=  4) return 0x08;
    return 0x00;
}
static uint8_t odr_g_code(uint16_t hz) {
    /* same codes as accel for simplicity */
    return odr_xl_code(hz);
}
static uint8_t fs_g_code(uint16_t dps) {
    /* 250=0x00, 500=0x04, 1000=0x08, 2000=0x0C */
    if (dps >= 2000) return 0x0C;
    if (dps >= 1000) return 0x08;
    if (dps >=  500) return 0x04;
    return 0x00;
}

/* ---------- GLOBALS ---------- */
static const struct device *i2c = DEVICE_DT_GET(IMU_I2C_NODE);
static const struct device *adc_dev = DEVICE_DT_GET(PIEZO_ADC_NODE);
static const struct device *gpio = DEVICE_DT_GET(IMU_INT_NODE);

static struct gpio_callback imu_cb;
static struct k_sem fifo_sem;           /* signaled on IMU INT */
static struct k_timer piezo_timer;      /* 1 kHz sampling */

static bool impact = false;
static int16_t last_peak_mv = 0;

/* ---------- I2C helpers ---------- */
static int imu_write(uint8_t reg, uint8_t val) {
    uint8_t buf[2] = { reg, val };
    return i2c_write(i2c, buf, 2, IMU_I2C_ADDR);
}
static int imu_read(uint8_t reg, uint8_t *val) {
    int rc = i2c_write_read(i2c, IMU_I2C_ADDR, &reg, 1, val, 1);
    return rc;
}
static int imu_read_burst(uint8_t reg, uint8_t *dst, size_t n) {
    return i2c_write_read(i2c, IMU_I2C_ADDR, &reg, 1, dst, n);
}

/* ---------- ADC helpers (mV) ---------- */
static int adc_gain = ADC_GAIN_1_4;  /* adjust per your front-end */
static int adc_ref  = ADC_REF_INTERNAL;
static int adc_res  = 12;

static int adc_setup_channel(void) {
    struct adc_channel_cfg cfg = {
        .gain = adc_gain,
        .reference = adc_ref,
        .acquisition_time = ADC_ACQ_TIME_DEFAULT,
        .channel_id = PIEZO_ADC_CH,
#ifdef CONFIG_ADC_CONFIGURABLE_INPUTS
        .input_positive = PIEZO_ADC_PIN,
#endif
    };
    return adc_channel_setup(adc_dev, &cfg);
}

static int read_adc_mv(int16_t *out_mv) {
    int16_t sample = 0;
    const struct adc_sequence seq = {
        .channels = BIT(PIEZO_ADC_CH),
        .buffer = &sample,
        .buffer_size = sizeof(sample),
        .resolution = 12,
        .oversampling = 0,
        .calibrate = false
    };
    int rc = adc_read(adc_dev, &seq);
    if (rc) return rc;

    /* Convert to millivolts using helper */
    int32_t mv = sample;
    adc_raw_to_millivolts(adc_ref, adc_gain, adc_res, &mv);
    *out_mv = (int16_t)mv;
    return 0;
}

/* ---------- PIEZO polling @1kHz ---------- */
static void piezo_timer_cb(struct k_timer *timer) {
    ARG_UNUSED(timer);
    int16_t mv = 0;
    if (read_adc_mv(&mv) == 0) {
        /* Threshold + hysteresis */
        if (!impact && mv > PIEZO_THR_MV) {
            impact = true;
            last_peak_mv = mv;
            LOG_INF("[piezo_impact] mv=%d ts=%u", mv, (uint32_t)k_uptime_get_32());
        } else if (impact && mv < (PIEZO_THR_MV - PIEZO_HYS_MV)) {
            impact = false; /* re-arm */
        }
    }
}

/* ---------- IMU IRQ (FIFO watermark) ---------- */
static void imu_int_cb(const struct device *dev, struct gpio_callback *cb, uint32_t pins) {
    ARG_UNUSED(dev); ARG_UNUSED(cb); ARG_UNUSED(pins);
    k_sem_give(&fifo_sem);
}

/* ---------- LSM6 init ---------- */
static int imu_init(void) {
    uint8_t who = 0;
    imu_read(REG_WHO_AM_I, &who);
    LOG_INF("LSM6 WHO_AM_I=0x%02x", who);

    /* Reset */
    imu_write(REG_CTRL3_C, 0x01);
    k_msleep(10);

    /* Accel: ODR + FS, Gyro: ODR + FS */
    uint8_t ctrl1_xl = odr_xl_code(IMU_ODR_HZ) | fs_xl_code(16);   /* 16g */
    uint8_t ctrl2_g  = odr_g_code(IMU_ODR_HZ)  | fs_g_code(2000);  /* 2000 dps */
    imu_write(REG_CTRL1_XL, ctrl1_xl);
    imu_write(REG_CTRL2_G,  ctrl2_g);

    /* FIFO: stream XL+G, watermark (set for ~2 frames) */
    /* Each frame = 12 bytes (ax..gz); at 104 Hz, 2 frames ~ 24 bytes */
    imu_write(REG_FIFO_CTRL1, 24);          /* watermark LSB */
    imu_write(REG_FIFO_CTRL2, 0x00);        /* watermark MSB */
    imu_write(REG_FIFO_CTRL3, 0x11);        /* decim: XL=1x, G=1x */
    imu_write(REG_FIFO_CTRL4, 0x06);        /* stream mode */

    /* Route FIFO th to INT1 (bit3 usually) */
    imu_write(REG_INT1_CTRL, 0x08);

    return 0;
}

/* Read all available FIFO bytes and print frames (ax,ay,az,gx,gy,gz) */
static void imu_drain_fifo(void) {
    uint8_t st1=0, st2=0;
    imu_read(REG_FIFO_STATUS1, &st1);
    imu_read(REG_FIFO_STATUS2, &st2);
    uint16_t fifo_level = ((uint16_t)st2 & 0x03) << 8 | st1;
    bool overrun = st2 & 0x40;

    if (overrun) {
        LOG_WRN("IMU FIFO overrun");
    }
    if (fifo_level < 12) return;

    /* Some variants use tagged FIFO. If so, use REG_FIFO_DATA_OUT_TAG path.
       Here we assume pure stream of 12B frames for clarity. */
    while (fifo_level >= 12) {
        uint8_t buf[12];
        imu_read_burst(REG_FIFO_DATA_OUT_X_L, buf, sizeof(buf));
        int16_t ax = (int16_t)(buf[1]<<8 | buf[0]);
        int16_t ay = (int16_t)(buf[3]<<8 | buf[2]);
        int16_t az = (int16_t)(buf[5]<<8 | buf[4]);
        int16_t gx = (int16_t)(buf[7]<<8 | buf[6]);
        int16_t gy = (int16_t)(buf[9]<<8 | buf[8]);
        int16_t gz = (int16_t)(buf[11]<<8 | buf[10]);

        /* TODO: convert to SI if needed; for now raw ticks */
        LOG_INF("[imu] ax=%d ay=%d az=%d gx=%d gy=%d gz=%d", ax,ay,az,gx,gy,gz);

        fifo_level -= 12;
    }
}

/* ---------- MAIN ---------- */
int main(void)
{
    /* Devices ready? */
    if (!device_is_ready(i2c))   { LOG_ERR("I2C not ready"); }
    if (!device_is_ready(gpio))  { LOG_ERR("GPIO not ready"); }
    if (!device_is_ready(adc_dev)){ LOG_ERR("ADC not ready"); }

    /* Setup IMU INT GPIO */
    gpio_pin_configure(gpio, IMU_INT_PIN, IMU_INT_FLAGS);
    gpio_pin_interrupt_configure(gpio, IMU_INT_PIN, GPIO_INT_EDGE_RISING);
    gpio_init_callback(&imu_cb, imu_int_cb, BIT(IMU_INT_PIN));
    gpio_add_callback(gpio, &imu_cb);

    /* Setup ADC (piezo peak node) */
    adc_setup_channel();
    k_timer_init(&piezo_timer, piezo_timer_cb, NULL);
    k_timer_start(&piezo_timer, K_MSEC(1000 / PIEZO_POLL_HZ), K_MSEC(1000 / PIEZO_POLL_HZ));

    /* Init IMU */
    imu_init();
    k_sem_init(&fifo_sem, 0, 1);

    LOG_INF("nRF54L15 IMU+Piezo demo started");

    while (1) {
        /* Wait for watermark IRQ, or timeout to still poll piezo-only runs */
        if (k_sem_take(&fifo_sem, K_MSEC(50)) == 0) {
            imu_drain_fifo();
        }
        /* You can also package & publish a payload here:
           - latest IMU frames read in imu_drain_fifo()
           - impact flag + last_peak_mv
           - timestamps via k_uptime_get() */
    }
    return 0;
}
