import time
import threading
import random
import customtkinter as ctk

# ---------------------------
# Basic setup
# ---------------------------
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# Fake sensor data thread
# (replace later
class SensorWorker(threading.Thread):
    def __init__(self, app):
        super().__init__(daemon=True)
        self.app = app
        self.running = True

    def run(self):
        while self.running:
            # Simulated values (replace with BLE later)
            light = 0       # lux
            temp = 0         # °C
            hum = 0            # %
            moisture = 0    # 

            self.app.update_sensors(light, temp, hum, moisture)
            time.sleep(1)

    def stop(self):
        self.running = False


# ---------------------------
# Main App
# ---------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart Sensing Agriculture_Poosti-Aguario")
        self.geometry("400x400")

        # Labels
        ctk.CTkLabel(self, text="Smart Sensing Agriculture_Poosti-Aguario", font=("Helvetica", 18)).pack(pady=(30, 0))

        ctk.CTkLabel(self, text="Light sensor:", font=("Arial", 14)).pack(pady=(20, 0))
        self.light_label = ctk.CTkLabel(self, text="-- lx", font=("Arial", 18, "bold"))
        self.light_label.pack()

        ctk.CTkLabel(self, text="Temperature / Humidity:", font=("Arial", 14)).pack(pady=(15, 0))
        self.th_label = ctk.CTkLabel(self, text="-- °C / -- %", font=("Arial", 18, "bold"))
        self.th_label.pack()

        ctk.CTkLabel(self, text="Grove Moisture sensor:", font=("Arial", 14)).pack(pady=(15, 0))
        self.moisture_label = ctk.CTkLabel(self, text="--", font=("Arial", 18, "bold"))
        self.moisture_label.pack()

        # Brightness control
        ctk.CTkLabel(self, text="Light brightness:", font=("Arial", 14)).pack(pady=(20, 0))
        self.brightness_slider = ctk.CTkSlider(
            self, from_=0, to=100, command=self.on_brightness_change
        )
        self.brightness_slider.set(50)
        self.brightness_slider.pack(pady=(5, 10))

        self.brightness_value = ctk.CTkLabel(self, text="50 %")
        self.brightness_value.pack()

        # "Start sensor simulation" it should be replaced with BLE connection later
        self.worker = SensorWorker(self)
        self.worker.start()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------------------------
    # Update GUI should be changed later to get real sensor data via BLE
    # ---------------------------
    def update_sensors(self, light, temp, hum, moisture):
        self.light_label.configure(text=f"{light:.0f} lx")
        self.th_label.configure(text=f"{temp:.1f} °C / {hum:.0f} %")
        self.moisture_label.configure(text=f"{moisture:.0f}")

    def on_brightness_change(self, value):
        value = int(value)
        self.brightness_value.configure(text=f"{value} %")

        # Later:
        # send brightness via BLE to AwoX bulb
        # ble.write_brightness(value)

    def on_close(self):
        self.worker.stop()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
