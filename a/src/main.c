#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/byteorder.h>
#include <hal/nrf_saadc.h>

/* ---------- ADC configuration ---------- */
#define ADC_NODE DT_NODELABEL(adc)
#define ADC_CHANNEL 1

static int16_t adc_buffer;
const struct device *adc_dev;

/* ---------- I2C / OPT3001 configuration ---------- */
#define I2C0_NODE DT_NODELABEL(i2c0)
const struct device *i2c0_dev;

#define OPT3001_ADDR 0x44
#define OPT3001_REG_RESULT 0x00
#define OPT3001_REG_CONFIG 0x01

/* Initialize OPT3001 sensor */
void opt3001_init(const struct device *i2c)
{
    uint16_t config = 0xC410; // Continuous conversion, auto-range
    uint8_t buf[3];

    buf[0] = OPT3001_REG_CONFIG;
    buf[1] = (config >> 8) & 0xFF;
    buf[2] = config & 0xFF;

    if (i2c_write(i2c, buf, 3, OPT3001_ADDR)) {
        printk("OPT3001 init failed\n");
    } else {
        printk("OPT3001 initialized\n");
    }
}

/* Read lux from OPT3001 using the same i2c_write + i2c_read method */
float opt3001_read_lux(const struct device *i2c)
{
    uint8_t reg = OPT3001_REG_RESULT;
    uint16_t raw;
    int ret;

    /* Write register address to the sensor */
    ret = i2c_write(i2c, &reg, sizeof(reg), OPT3001_ADDR);
    if (ret != 0) {
        printk("Error writing register for lux read: %d\n", ret);
        return -1;
    }

    /* Read 2 bytes from the sensor */
    ret = i2c_read(i2c, (uint8_t *)&raw, sizeof(raw), OPT3001_ADDR);
    if (ret != 0) {
        printk("Error reading lux: %d\n", ret);
        return -1;
    }

    /* Convert from big-endian */
    raw = sys_be16_to_cpu(raw);

    /* Decode lux value */
    uint16_t mantissa = raw & 0x0FFF;
    uint8_t exponent = (raw >> 12) & 0x0F;

    float lux = mantissa * (0.01f * (1 << exponent));
    return lux;
}

/* ---------- Main function ---------- */
void main(void)
{
    printk("Starting ADC + OPT3001 example\n");

    /* ----- ADC setup ----- */
    adc_dev = DEVICE_DT_GET(ADC_NODE);
    if (!device_is_ready(adc_dev)) {
        printk("ADC device not ready\n");
        return;
    }

    struct adc_channel_cfg adc_cfg = {
        .gain = ADC_GAIN_1_6,
        .reference = ADC_REF_INTERNAL,
        .acquisition_time = ADC_ACQ_TIME_DEFAULT,
        .channel_id = ADC_CHANNEL,
        .input_positive = NRF_SAADC_INPUT_AIN1,
    };
    adc_channel_setup(adc_dev, &adc_cfg);

    struct adc_sequence seq = {
        .channels = BIT(ADC_CHANNEL),
        .buffer = &adc_buffer,
        .buffer_size = sizeof(adc_buffer),
        .resolution = 12,
    };

    /* ----- I2C / OPT3001 setup ----- */
    i2c0_dev = DEVICE_DT_GET(I2C0_NODE);
    if (!device_is_ready(i2c0_dev)) {
        printk("I2C0 device not ready\n");
        return;
    }

    opt3001_init(i2c0_dev);

    /* ----- Main loop ----- */
    while (1) {
        /* Read ADC (moisture sensor) */
        if (adc_read(adc_dev, &seq) == 0) {
            int moisture = adc_buffer;
            printk("Moisture: %d | ", moisture);
        } else {
            printk("ADC read error\n");
        }

        /* Read light from OPT3001 */
        float lux = opt3001_read_lux(i2c0_dev);
        if (lux >= 0) {
            /* Print lux without enabling float support */
            int lux_int = (int)lux;
            int lux_frac = (int)(lux * 100) % 100;
            printk("Light: %d.%02d lux\n", lux_int, lux_frac);
        }

        k_sleep(K_SECONDS(1));
    }
}
