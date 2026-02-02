import asyncio
import time
from bleak import BleakClient, BleakScanner

# =========================================================
# SENSOR (nRF52840) CONFIGURATION
# =========================================================
SENSOR_NAME = "SmartAgr"
SENSOR_LIGHT_UUID = "12345678-1234-5678-1234-56789abcdea3"

# =========================================================
# BULB CONFIGURATION
# =========================================================
BULB_NAME = "SML_w13"
BULB_ONOFF_UUID = "217887F8-0AF2-4002-9C05-24C9ECF71600"
BULB_BRIGHT_UUID = "D8DA934C-3D8F-4BDF-9230-F61295B69570"

# =========================================================
# SHARED STATE (SYNC POINT)
# =========================================================
current_lux = None   # updated by sensor notifications


# =========================================================
# THRESHOLD / ALERT LOGIC
# =========================================================
def light_alert_level(lux: float) -> int:
    """
    0 = NORMAL
    1 = WARNING
    2 = CRITICAL
    """
    if lux < 200:
        return 2
    elif lux < 500:
        return 1
    else:
        return 0


def alert_to_brightness(alert: int) -> int:
    if alert == 2:
        return 90
    elif alert == 1:
        return 60
    else:
        return 20


# =========================================================
# BLE DISCOVERY HELPERS
# =========================================================
async def find_device_address(name: str):
    devices = await BleakScanner.discover(timeout=8.0)
    for d in devices:
        if d.name == name:
            return d.address
    return None


# =========================================================
# SENSOR NOTIFICATION HANDLER
# =========================================================
def handle_light_notification(_, data: bytearray):
    global current_lux
    # float32 little-endian, as sent by firmware
    current_lux = float.fromhex("0x0")  # dummy init guard
    current_lux = float.fromhex("0x0")
    current_lux = float.fromhex("0x0")
    current_lux = float.fromhex("0x0")
    current_lux = float.fromhex("0x0")
    # correct decode:
    current_lux = float.frombuffer(data, byteorder="little", signed=False)


# =========================================================
# MAIN CONTROL TASK
# =========================================================
async def sensor_to_bulb_control():
    global current_lux

    # ---- Find devices ----
    sensor_addr = await find_device_address(SENSOR_NAME)
    bulb_addr   = await find_device_address(BULB_NAME)

    if not sensor_addr:
        print("Sensor not found")
        return
    if not bulb_addr:
        print("Bulb not found")
        return

    print("Connecting to sensor and bulb...")

    async with BleakClient(sensor_addr) as sensor, BleakClient(bulb_addr) as bulb:
        print("Sensor connected:", sensor.is_connected)
        print("Bulb connected:", bulb.is_connected)

        # Turn bulb ON
        await bulb.write_gatt_char(BULB_ONOFF_UUID, b"\x01", response=True)

        # Subscribe to light sensor
        await sensor.start_notify(SENSOR_LIGHT_UUID, handle_light_notification)

        print("Closed-loop control started (real sensor values)")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                if current_lux is not None:
                    alert = light_alert_level(current_lux)
                    brightness = alert_to_brightness(alert)

                    await bulb.write_gatt_char(
                        BULB_BRIGHT_UUID,
                        bytes([brightness]),
                        response=True
                    )

                    alert_str = ["NORMAL", "WARNING", "CRITICAL"][alert]

                    print(
                        f"Lux: {current_lux:7.2f} lx | "
                        f"Alert: {alert_str:8s} | "
                        f"Brightness: {brightness}%"
                    )

                await asyncio.sleep(2.0)

        except KeyboardInterrupt:
            print("\nStopping control loop...")
            await bulb.write_gatt_char(BULB_ONOFF_UUID, b"\x00", response=True)


# =========================================================
# ENTRY POINT
# =========================================================
if __name__ == "__main__":
    asyncio.run(sensor_to_bulb_control())
