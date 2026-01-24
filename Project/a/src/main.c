#include <zephyr/kernel.h>
#include <zephyr/device.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/drivers/i2c.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/byteorder.h>
#include <hal/nrf_saadc.h>

#include <zephyr/bluetooth/bluetooth.h>
#include <zephyr/bluetooth/gatt.h>
#include <zephyr/bluetooth/conn.h>
#include <zephyr/bluetooth/uuid.h>

/* ---------- ADC configuration ---------- */
#define ADC_NODE DT_NODELABEL(adc)
#define ADC_CHANNEL 1
static int16_t adc_buffer;
const struct device *adc_dev;

/* ---------- I2C configuration ---------- */
#define I2C0_NODE DT_NODELABEL(i2c0)
#define I2C1_NODE DT_NODELABEL(i2c1)
const struct device *i2c0_dev;
const struct device *i2c1_dev;

#define OPT3001_ADDR 0x44
#define OPT3001_REG_RESULT 0x00
#define OPT3001_REG_CONFIG 0x01

#define SHTC3_ADDR 0x70
#define SHTC3_MEASURE_TEMP_CMD 0x7866

/* ---------- Custom BLE UUIDs ---------- */
#define BT_UUID_ENV_SERVICE_VAL \
    BT_UUID_128_ENCODE(0x12345678, 0x1234, 0x5678, 0x1234, 0x56789abcdea0)

#define BT_UUID_ENV_SERVICE BT_UUID_DECLARE_128(BT_UUID_ENV_SERVICE_VAL)
#define BT_UUID_ENV_TEMP    BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x12345678, 0x1234, 0x5678, 0x1234, 0x56789abcdea1))
#define BT_UUID_ENV_MOIST   BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x12345678, 0x1234, 0x5678, 0x1234, 0x56789abcdea2))
#define BT_UUID_ENV_LIGHT   BT_UUID_DECLARE_128(BT_UUID_128_ENCODE(0x12345678, 0x1234, 0x5678, 0x1234, 0x56789abcdea3))

/* ---------- BLE service definition ---------- */
BT_GATT_SERVICE_DEFINE(env_svc,
    BT_GATT_PRIMARY_SERVICE(BT_UUID_ENV_SERVICE),

    BT_GATT_CHARACTERISTIC(BT_UUID_ENV_TEMP,
        BT_GATT_CHRC_NOTIFY,
        BT_GATT_PERM_READ,
        NULL, NULL, NULL),
    BT_GATT_CCC(NULL, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),

    BT_GATT_CHARACTERISTIC(BT_UUID_ENV_MOIST,
        BT_GATT_CHRC_NOTIFY,
        BT_GATT_PERM_READ,
        NULL, NULL, NULL),
    BT_GATT_CCC(NULL, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE),

    BT_GATT_CHARACTERISTIC(BT_UUID_ENV_LIGHT,
        BT_GATT_CHRC_NOTIFY,
        BT_GATT_PERM_READ,
        NULL, NULL, NULL),
    BT_GATT_CCC(NULL, BT_GATT_PERM_READ | BT_GATT_PERM_WRITE)
);

/* ---------- Advertising data ---------- */
static const struct bt_data ad[] = {
    BT_DATA_BYTES(BT_DATA_FLAGS, (BT_LE_AD_GENERAL | BT_LE_AD_NO_BREDR)),
    BT_DATA_BYTES(BT_DATA_UUID128_ALL, BT_UUID_ENV_SERVICE_VAL),
};

/* ---------- Sensor functions ---------- */
void opt3001_init(const struct device *i2c)
{
    uint8_t buf[3] = { OPT3001_REG_CONFIG, 0xC4, 0x10 };
    if (i2c_write(i2c, buf, 3, OPT3001_ADDR)) {
        printk("OPT3001 init failed\n");
    }
}

float opt3001_read_lux(const struct device *i2c)
{
    uint8_t reg = OPT3001_REG_RESULT;
    uint16_t raw;

    if (i2c_write_read(i2c, OPT3001_ADDR, &reg, 1, &raw, 2)) {
        return -1.0f;
    }

    raw = sys_be16_to_cpu(raw);
    return (raw & 0x0FFF) * (0.01f * (1 << ((raw >> 12) & 0x0F)));
}

float read_shtc3_temp(const struct device *i2c)
{
    uint8_t cmd[2] = {
        (SHTC3_MEASURE_TEMP_CMD >> 8) & 0xFF,
        SHTC3_MEASURE_TEMP_CMD & 0xFF
    };

    uint8_t buf[3];

    if (i2c_write(i2c, cmd, 2, SHTC3_ADDR)) {
        return -1000.0f;
    }

    k_sleep(K_MSEC(15));

    if (i2c_read(i2c, buf, 3, SHTC3_ADDR)) {
        return -1000.0f;
    }

    return -45.0f + 175.0f * (((buf[0] << 8) | buf[1]) / 65535.0f);
}

/* ---------- Workqueue + Timer ---------- */
struct k_work sensor_work;


void sensor_timer_handler(struct k_timer *timer);

void sensor_work_handler(struct k_work *work)
{
    int16_t adc_val = -1;

    struct adc_sequence seq = {
        .channels    = BIT(ADC_CHANNEL),
        .buffer      = &adc_buffer,
        .buffer_size = sizeof(adc_buffer),
        .resolution  = 12,
    };

    if (adc_read(adc_dev, &seq) == 0) {
        adc_val = adc_buffer;
    }

    float lux  = opt3001_read_lux(i2c0_dev);
    float temp = read_shtc3_temp(i2c1_dev);

    bt_gatt_notify(NULL, &env_svc.attrs[1], &temp, sizeof(temp));
    bt_gatt_notify(NULL, &env_svc.attrs[4], &adc_val, sizeof(adc_val));
    bt_gatt_notify(NULL, &env_svc.attrs[7], &lux, sizeof(lux));

    printk("Temp: %.2f C | Moisture: %d | Light: %.2f lx\n",
           (double)temp, adc_val, (double)lux);
}


K_TIMER_DEFINE(sensor_timer, sensor_timer_handler, NULL);

void sensor_timer_handler(struct k_timer *timer)
{
    k_work_submit(&sensor_work);
}

/* ---------- Bluetooth ---------- */
static void bt_ready(int err)
{
    if (err) {
        printk("Bluetooth init failed (%d)\n", err);
        return;
    }

    printk("Bluetooth initialized\n");

    int adv_err = bt_le_adv_start(
        BT_LE_ADV_PARAM(
            BT_LE_ADV_OPT_CONNECTABLE | BT_LE_ADV_OPT_USE_NAME,
            BT_GAP_ADV_FAST_INT_MIN_2,
            BT_GAP_ADV_FAST_INT_MAX_2,
            NULL),
        ad, ARRAY_SIZE(ad),
        NULL, 0);

    if (adv_err) {
        printk("Advertising failed (%d)\n", adv_err);
        return;
    }

    printk("Advertising successfully started\n");
}


int main(void)
{
    printk("Starting Environmental BLE Sensor...\n");

    adc_dev  = DEVICE_DT_GET(ADC_NODE);
    i2c0_dev = DEVICE_DT_GET(I2C0_NODE);
    i2c1_dev = DEVICE_DT_GET(I2C1_NODE);

    if (!device_is_ready(adc_dev) ||
        !device_is_ready(i2c0_dev) ||
        !device_is_ready(i2c1_dev)) {
        printk("Device not ready\n");
        return 0;
    }

    struct adc_channel_cfg adc_cfg = {
        .gain             = ADC_GAIN_1_6,
        .reference        = ADC_REF_INTERNAL,
        .acquisition_time = ADC_ACQ_TIME_DEFAULT,
        .channel_id       = ADC_CHANNEL,
        .input_positive   = NRF_SAADC_INPUT_AIN1,
    };

    adc_channel_setup(adc_dev, &adc_cfg);
    opt3001_init(i2c0_dev);

    k_work_init(&sensor_work, sensor_work_handler);

    int bt_err = bt_enable(bt_ready);
    if (bt_err) {
        printk("Bluetooth enable failed (%d)\n", bt_err);
        return 0;
    }

    k_timer_start(&sensor_timer, K_SECONDS(2), K_SECONDS(2));

    while (1) {
        k_sleep(K_FOREVER);
    }
}
