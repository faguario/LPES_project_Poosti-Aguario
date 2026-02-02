import time
import threading
import asyncio
import struct
import customtkinter as ctk
from bleak import BleakClient, BleakScanner

# SENSOR CONFIGURATION
SENSOR_NAME = "SmartAgr"
TEMP_CHAR_UUID  = "12345678-1234-5678-1234-56789abcdea1"
MOIST_CHAR_UUID = "12345678-1234-5678-1234-56789abcdea2"
LIGHT_CHAR_UUID = "12345678-1234-5678-1234-56789abcdea3"

# BULB CONFIGURATION
BULB_NAME = "SML_w13"
BULB_ONOFF_UUID  = "217887F8-0AF2-4002-9C05-24C9ECF71600"
BULB_BRIGHT_UUID = "D8DA934C-3D8F-4BDF-9230-F61295B69570"

# SHARED STATE
ble_data = {
    "light": 0.0,
    "temp": 0.0,
    "moisture": 0.0
}

last_brightness = None

# ALERT / THRESHOLD LOGIC
def light_alert(lux):
    if lux < 200: return 2
    elif lux < 600: return 1
    else: return 0

def temp_alert(temp):
    if temp < 10 or temp > 30: return 2
    elif temp < 18: return 1
    else: return 0

def moisture_alert(m):
    if m < 300: return 2
    elif m < 600: return 1
    else: return 0

def alert_to_brightness(alert):
    return {2: 90, 1: 60, 0: 20}[alert]

def alert_color(alert):
    return {2: "#E74C3C", 1: "#F1C40F", 0: "#2ECC71"}[alert]

def alert_text(alert):
    return ["NORMAL", "WARNING", "CRITICAL"][alert]

# BLE NOTIFICATION HANDLERS
def handle_temp(_, data):
    ble_data["temp"] = struct.unpack("<f", data)[0]

def handle_moist(_, data):
    ble_data["moisture"] = struct.unpack("<h", data)[0]

def handle_light(_, data):
    ble_data["light"] = struct.unpack("<f", data)[0]

# BLE TASK (SENSOR + BULB)
async def ble_task():
    global last_brightness

    devices = await BleakScanner.discover(timeout=6)
    sensor_addr = bulb_addr = None

    for d in devices:
        if d.name == SENSOR_NAME:
            sensor_addr = d.address
        if d.name == BULB_NAME:
            bulb_addr = d.address

    if not sensor_addr or not bulb_addr:
        print("Sensor or bulb not found")
        return

    async with BleakClient(sensor_addr) as sensor, BleakClient(bulb_addr) as bulb:
        await bulb.write_gatt_char(BULB_ONOFF_UUID, b"\x01", response=True)

        await sensor.start_notify(TEMP_CHAR_UUID, handle_temp)
        await sensor.start_notify(MOIST_CHAR_UUID, handle_moist)
        await sensor.start_notify(LIGHT_CHAR_UUID, handle_light)

        while True:
            lux = ble_data["light"]
            alert = light_alert(lux)
            brightness = alert_to_brightness(alert)

            if brightness != last_brightness:
                await bulb.write_gatt_char(
                    BULB_BRIGHT_UUID, bytes([brightness]), response=True
                )
                last_brightness = brightness

            await asyncio.sleep(1.5)

def start_ble():
    asyncio.run(ble_task())

# GUI
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class SensorWorker(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app

    def run(self):
        while True:
            self.app.after(
                0,
                self.app.update_sensors,
                ble_data["light"],
                ble_data["temp"],
                ble_data["moisture"]
            )
            time.sleep(1)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Smart Agriculture – Alerts")
        self.geometry("420x500")

        ctk.CTkLabel(self, text="Smart Sensing Agriculture", font=("Helvetica", 18)).pack(pady=20)

        self.light_lbl = ctk.CTkLabel(self, text="Light: -- lx", font=("Arial", 16))
        self.light_lbl.pack()
        self.light_status = ctk.CTkLabel(self, text="Status: --", font=("Arial", 14))
        self.light_status.pack(pady=5)

        self.temp_lbl = ctk.CTkLabel(self, text="Temp: -- °C", font=("Arial", 16))
        self.temp_lbl.pack()
        self.temp_status = ctk.CTkLabel(self, text="Status: --", font=("Arial", 14))
        self.temp_status.pack(pady=5)

        self.moist_lbl = ctk.CTkLabel(self, text="Moisture: --", font=("Arial", 16))
        self.moist_lbl.pack()
        self.moist_status = ctk.CTkLabel(self, text="Status: --", font=("Arial", 14))
        self.moist_status.pack(pady=5)

        threading.Thread(target=start_ble, daemon=True).start()
        SensorWorker(self).start()

    def update_sensors(self, light, temp, moist):
        la = light_alert(light)
        ta = temp_alert(temp)
        ma = moisture_alert(moist)

        self.light_lbl.configure(text=f"Light: {light:.1f} lx")
        self.light_status.configure(text=alert_text(la), text_color=alert_color(la))

        self.temp_lbl.configure(text=f"Temp: {temp:.1f} °C")
        self.temp_status.configure(text=alert_text(ta), text_color=alert_color(ta))

        self.moist_lbl.configure(text=f"Moisture: {moist:.0f}")
        self.moist_status.configure(text=alert_text(ma), text_color=alert_color(ma))

if __name__ == "__main__":
    app = App()
    app.mainloop()
