#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>

/* ADC */
#define ADC_NODE DT_NODELABEL(adc)
#define ADC_CHANNEL 1
static int16_t adc_buffer;
const struct device *adc_dev;

/* I2C devices */
#define I2C0_NODE DT_NODELABEL(i2c0)
#define I2C1_NODE DT_NODELABEL(i2c1)

const struct device *i2c0_dev;
const struct device *i2c1_dev;

/* OPT3001 on I2C0 */
#define OPT3001_ADDR 0x44
#define OPT3001_REG_RESULT 0x00
#define OPT3001_REG_CONFIG 0x01

void opt3001_init(const struct device *i2c)
{
    uint16_t config = 0x10C4; // Continuous conversion, automatic range
    uint8_t buf[3];

    buf[0] = OPT3001_REG_CONFIG;
    buf[1] = (config >> 8) & 0xFF;
    buf[2] = config & 0xFF;

    if (i2c_write(i2c, buf, 3, OPT3001_ADDR)) {
        printk("OPT3001 init failed\n");
    }
}

float opt3001_read_lux(const struct device *i2c)
{
    uint8_t buf[2];
    uint16_t raw;

    if (i2c_burst_read(i2c, OPT3001_ADDR, OPT3001_REG_RESULT, buf, 2)) {
        printk("OPT3001 read failed\n");
        return -1;
    }

    raw = (buf[0] << 8) | buf[1];
    uint16_t mantissa = raw & 0x0FFF;
    uint8_t exponent = (raw >> 12) & 0x0F;

    return mantissa * (0.01f * (1 << exponent));
}

/* Temperature sensor on I2C1 */
#define TEMP_ADDR 0x48

float read_temperature(const struct device *i2c)
{
    uint8_t buf[2];
    int16_t raw;

    if (i2c_burst_read(i2c, TEMP_ADDR, 0x00, buf, 2)) {
        printk("Temperature read failed\n");
        return -1000; // error value
    }

    raw = (buf[0] << 8) | buf[1];
    raw >>= 4;

    return raw * 0.0625f;
}

void main(void)
{
    printk("Smart Agriculture App Started\n");

    /* ADC */
    adc_dev = DEVICE_DT_GET(ADC_NODE);
    if (!device_is_ready(adc_dev)) {
        printk("ADC not ready\n");
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

    /* I2C0 */
    i2c0_dev = DEVICE_DT_GET(I2C0_NODE);
    if (!device_is_ready(i2c0_dev)) {
        printk("I2C0 not ready\n");
        return;
    }
    opt3001_init(i2c0_dev);

    /* I2C1 */
    i2c1_dev = DEVICE_DT_GET(I2C1_NODE);
    if (!device_is_ready(i2c1_dev)) {
        printk("I2C1 not ready\n");
        return;
    }

    while (1) {
        /* Moisture */
        if (adc_read(adc_dev, &seq) == 0) {
            int moisture = adc_buffer;
            printk("Moisture: %d | ", moisture);
        }

        /* Light */
        float lux = opt3001_read_lux(i2c0_dev);
        printk("Light: %.2f lux | ", lux);

        /* Temperature */
        float temp = read_temperature(i2c1_dev);
        printk("Temp: %.2f C\n", temp);

        k_sleep(K_SECONDS(1));
    }
}
