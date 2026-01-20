"""
Smart Sensing Agriculture via BLE — GUI skeleton (CustomTkinter)

What this gives you (optimized for your project, not YouTube):
- Clean modern layout (sidebar + main cards)
- Live sensor tiles: Temperature / Humidity / Light
- Connection controls (Scan / Connect / Disconnect)
- Threshold slider + Auto/Manual mode
- Status + log console
- Thread-safe update hooks so BLE can run in background without freezing GUI

Next step: plug your bleak BLE code into BLEWorker.run().
"""

import time
import threading
import queue
import random
import tkinter as tk
import customtkinter as ctk

ctk.set_appearance_mode("System")   # "Light" / "Dark" / "System"
ctk.set_default_color_theme("blue") # try "green" if you want a “plant vibe”


# ---------------------------
# Utility formatting
# ---------------------------
def fmt(v, unit="", nd=1):
    if v is None:
        return "--" + (f" {unit}" if unit else "")
    return f"{v:.{nd}f}{(' ' + unit) if unit else ''}"


# ---------------------------
# BLE worker (placeholder)
# Replace with bleak code
# ---------------------------
class BLEWorker(threading.Thread):
    """
    Runs BLE operations off the UI thread.
    Communicates with the GUI via:
      - event_q: dict messages {type: "...", ...}
      - stop_event: signal to exit
    """
    def __init__(self, event_q: queue.Queue, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.event_q = event_q
        self.stop_event = stop_event
        self.connected = False
        self.device_name = None

        # Example “state” (replace with real notifications)
        self.temp = None
        self.hum = None
        self.lux = None

    def scan(self):
        # Replace with BLE scan results from bleak
        fake = [
            {"name": "nRF52840_SensorNode", "addr": "AA:BB:CC:11:22:33", "rssi": -48},
            {"name": "AwoX SmartLight",      "addr": "DD:EE:FF:44:55:66", "rssi": -60},
        ]
        self.event_q.put({"type": "scan_results", "devices": fake})

    def connect(self, addr: str):
        # Replace with bleak connect
        self.connected = True
        self.device_name = addr
        self.event_q.put({"type": "status", "level": "ok", "text": f"Connected to {addr}"})

    def disconnect(self):
        # Replace with bleak disconnect
        self.connected = False
        self.device_name = None
        self.event_q.put({"type": "status", "level": "warn", "text": "Disconnected"})

    def set_light_brightness(self, percent: int):
        # Replace with AwoX write_gatt_char
        self.event_q.put({"type": "status", "level": "ok", "text": f"AwoX brightness -> {percent}%"})

    def run(self):
        """
        Demo data loop. Replace this section with:
        - connect to sensor node
        - subscribe to notifications
        - push updates to event_q as they arrive
        """
        t0 = time.time()
        while not self.stop_event.is_set():
            if self.connected:
                # simulate sensor drift
                dt = time.time() - t0
                self.temp = 22 + 1.5 * random.random()
                self.hum  = 45 + 10 * random.random()
                self.lux  = 120 + 80 * random.random()

                self.event_q.put({
                    "type": "sensor_update",
                    "temp_c": self.temp,
                    "hum_pct": self.hum,
                    "lux": self.lux,
                    "ts": time.time()
                })
            time.sleep(0.5)


# ---------------------------
# Main App
# ---------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("920x560")
        self.minsize(860, 520)
        self.title("Smart Sensing Agriculture via BLE")

        # Thread comms
        self.event_q = queue.Queue()
        self.stop_event = threading.Event()
        self.ble = BLEWorker(self.event_q, self.stop_event)
        self.ble.start()

        # Control state
        self.auto_mode = tk.BooleanVar(value=True)
        self.lux_threshold = tk.IntVar(value=150)
        self.manual_brightness = tk.IntVar(value=60)
        self.last_lux = None

        self._build_layout()
        self._poll_events()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    # ---------- UI ----------
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, corner_radius=16)
        self.sidebar.grid(row=0, column=0, sticky="nsw", padx=14, pady=14)
        self.sidebar.grid_rowconfigure(99, weight=1)

        self.app_title = ctk.CTkLabel(
            self.sidebar, text="Smart Agriculture", font=ctk.CTkFont(size=18, weight="bold")
        )
        self.app_title.grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")

        self.sub_title = ctk.CTkLabel(
            self.sidebar, text="BLE Sensors + AwoX Actuator", text_color=("gray35", "gray70")
        )
        self.sub_title.grid(row=1, column=0, padx=14, pady=(0, 12), sticky="w")

        # Scan/Connect
        self.btn_scan = ctk.CTkButton(self.sidebar, text="Scan devices", command=self.on_scan)
        self.btn_scan.grid(row=2, column=0, padx=14, pady=(6, 8), sticky="ew")

        self.device_menu = ctk.CTkOptionMenu(self.sidebar, values=["(scan first)"])
        self.device_menu.grid(row=3, column=0, padx=14, pady=(0, 10), sticky="ew")

        self.btn_connect = ctk.CTkButton(self.sidebar, text="Connect", command=self.on_connect)
        self.btn_connect.grid(row=4, column=0, padx=14, pady=(0, 8), sticky="ew")

        self.btn_disconnect = ctk.CTkButton(
            self.sidebar, text="Disconnect", fg_color="transparent", border_width=1,
            text_color=("gray20", "gray90"), command=self.on_disconnect
        )
        self.btn_disconnect.grid(row=5, column=0, padx=14, pady=(0, 14), sticky="ew")

        # Control mode
        self.mode_label = ctk.CTkLabel(self.sidebar, text="Light control", font=ctk.CTkFont(weight="bold"))
        self.mode_label.grid(row=6, column=0, padx=14, pady=(4, 6), sticky="w")

        self.mode_switch = ctk.CTkSwitch(
            self.sidebar, text="Auto (based on ambient light)", variable=self.auto_mode,
            command=self.on_mode_change
        )
        self.mode_switch.grid(row=7, column=0, padx=14, pady=(0, 10), sticky="w")
        self.mode_switch.select()  # default ON

        # Threshold slider
        self.th_label = ctk.CTkLabel(self.sidebar, text=f"Lux threshold: {self.lux_threshold.get()} lx")
        self.th_label.grid(row=8, column=0, padx=14, pady=(0, 6), sticky="w")

        self.th_slider = ctk.CTkSlider(
            self.sidebar, from_=10, to=1000, number_of_steps=99,
            command=self.on_threshold_slider
        )
        self.th_slider.set(self.lux_threshold.get())
        self.th_slider.grid(row=9, column=0, padx=14, pady=(0, 12), sticky="ew")

        # Manual brightness slider
        self.mb_label = ctk.CTkLabel(self.sidebar, text=f"Manual brightness: {self.manual_brightness.get()}%")
        self.mb_label.grid(row=10, column=0, padx=14, pady=(0, 6), sticky="w")

        self.mb_slider = ctk.CTkSlider(
            self.sidebar, from_=0, to=100, number_of_steps=100,
            command=self.on_manual_brightness
        )
        self.mb_slider.set(self.manual_brightness.get())
        self.mb_slider.grid(row=11, column=0, padx=14, pady=(0, 8), sticky="ew")

        self.btn_apply = ctk.CTkButton(self.sidebar, text="Apply brightness", command=self.apply_brightness)
        self.btn_apply.grid(row=12, column=0, padx=14, pady=(0, 10), sticky="ew")

        # Status pill
        self.status = ctk.CTkLabel(
            self.sidebar, text="Status: idle", corner_radius=10, padx=10, pady=6,
            fg_color=("gray90", "gray20")
        )
        self.status.grid(row=98, column=0, padx=14, pady=(10, 14), sticky="ew")

        # Main area
        self.main = ctk.CTkFrame(self, corner_radius=16)
        self.main.grid(row=0, column=1, sticky="nsew", padx=(0, 14), pady=14)
        self.main.grid_columnconfigure((0, 1, 2), weight=1)
        self.main.grid_rowconfigure(2, weight=1)

        header = ctk.CTkLabel(self.main, text="Live Environment", font=ctk.CTkFont(size=20, weight="bold"))
        header.grid(row=0, column=0, columnspan=3, padx=18, pady=(18, 10), sticky="w")

        # Sensor cards
        self.card_temp = self._make_card(self.main, "Temperature", "-- °C")
        self.card_hum  = self._make_card(self.main, "Humidity", "-- %")
        self.card_lux  = self._make_card(self.main, "Ambient Light", "-- lx")

        self.card_temp.grid(row=1, column=0, padx=14, pady=(0, 14), sticky="nsew")
        self.card_hum.grid(row=1, column=1, padx=14, pady=(0, 14), sticky="nsew")
        self.card_lux.grid(row=1, column=2, padx=14, pady=(0, 14), sticky="nsew")

        # Log console
        self.log = ctk.CTkTextbox(self.main, corner_radius=12)
        self.log.grid(row=2, column=0, columnspan=3, padx=14, pady=(0, 14), sticky="nsew")
        self._log("Ready. Click 'Scan devices'.")

    def _make_card(self, parent, title, value_text):
        frame = ctk.CTkFrame(parent, corner_radius=16)
        frame.grid_columnconfigure(0, weight=1)

        t = ctk.CTkLabel(frame, text=title, text_color=("gray35", "gray70"))
        t.grid(row=0, column=0, padx=14, pady=(12, 0), sticky="w")

        v = ctk.CTkLabel(frame, text=value_text, font=ctk.CTkFont(size=28, weight="bold"))
        v.grid(row=1, column=0, padx=14, pady=(4, 12), sticky="w")

        # store reference
        frame.value_label = v
        return frame

    # ---------- Actions ----------
    def on_scan(self):
        self._set_status("Scanning...", level="warn")
        self._log("Scanning for BLE devices...")
        self.ble.scan()

    def on_connect(self):
        choice = self.device_menu.get()
        if choice.startswith("(scan"):
            self._log("Scan first.")
            return
        # choice format: "NAME | ADDR | RSSI"
        addr = choice.split("|")[1].strip()
        self._log(f"Connecting to {addr}...")
        self.ble.connect(addr)
        self._set_status("Connected", level="ok")

    def on_disconnect(self):
        self.ble.disconnect()
        self._set_status("Disconnected", level="warn")

    def on_mode_change(self):
        mode = "AUTO" if self.auto_mode.get() else "MANUAL"
        self._log(f"Mode -> {mode}")

    def on_threshold_slider(self, v):
        v = int(v)
        self.lux_threshold.set(v)
        self.th_label.configure(text=f"Lux threshold: {v} lx")

    def on_manual_brightness(self, v):
        v = int(v)
        self.manual_brightness.set(v)
        self.mb_label.configure(text=f"Manual brightness: {v}%")

    def apply_brightness(self):
        if not self.ble.connected:
            self._log("Not connected to bulb/actuator (placeholder logic).")
            # In your final version, you'll likely connect to AwoX separately.
        percent = int(self.manual_brightness.get())
        self._log(f"Applying manual brightness: {percent}%")
        self.ble.set_light_brightness(percent)

    # ---------- Event handling ----------
    def _poll_events(self):
        """
        Runs in UI thread. Pulls messages from event_q and updates UI.
        """
        try:
            while True:
                msg = self.event_q.get_nowait()
                self._handle_event(msg)
        except queue.Empty:
            pass

        # keep polling
        self.after(100, self._poll_events)

    def _handle_event(self, msg: dict):
        t = msg.get("type")

        if t == "scan_results":
            devices = msg["devices"]
            if not devices:
                self.device_menu.configure(values=["(none found)"])
                self.device_menu.set("(none found)")
                self._set_status("No devices found", level="warn")
                return

            values = [f'{d["name"]} | {d["addr"]} | RSSI {d["rssi"]} dBm' for d in devices]
            self.device_menu.configure(values=values)
            self.device_menu.set(values[0])
            self._log(f"Found {len(devices)} device(s).")

        elif t == "sensor_update":
            temp = msg.get("temp_c")
            hum  = msg.get("hum_pct")
            lux  = msg.get("lux")

            self.card_temp.value_label.configure(text=fmt(temp, "°C", 1))
            self.card_hum.value_label.configure(text=fmt(hum, "%", 0))
            self.card_lux.value_label.configure(text=fmt(lux, "lx", 0))

            # Auto-control example (closed loop)
            self.last_lux = lux
            if self.auto_mode.get() and lux is not None:
                thr = self.lux_threshold.get()
                # Simple control law: below threshold -> brighten, above -> dim
                target = 80 if lux < thr else 20
                self.ble.set_light_brightness(target)
                self._log(f"AUTO: lux={int(lux)} <thr={thr}? -> brightness {target}%")

        elif t == "status":
            level = msg.get("level", "ok")
            text = msg.get("text", "")
            self._set_status(text, level=level)
            self._log(text)

        else:
            self._log(f"Unhandled event: {msg}")

    # ---------- UI helpers ----------
    def _log(self, s: str):
        ts = time.strftime("%H:%M:%S")
        self.log.insert("end", f"[{ts}] {s}\n")
        self.log.see("end")

    def _set_status(self, text: str, level="ok"):
        # Simple “pill” status
        if level == "ok":
            fg = ("#D7FBE8", "#1F3B2C")
            tc = ("#0F2E1E", "#CFF7E5")
        elif level == "warn":
            fg = ("#FFF3CD", "#3A2F10")
            tc = ("#3A2F10", "#FFE9A6")
        else:
            fg = ("#F8D7DA", "#3B1F21")
            tc = ("#3B1F21", "#F8D7DA")

        self.status.configure(text=f"Status: {text}", fg_color=fg, text_color=tc)

    def on_close(self):
        self.stop_event.set()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
