import asyncio
from bleak import BleakClient, BleakScanner
import struct

DEVICE_NAME = "SmartAgr"

TEMP_CHAR_UUID  = "12345678-1234-5678-1234-56789abcdea1"
MOIST_CHAR_UUID = "12345678-1234-5678-1234-56789abcdea2"
LIGHT_CHAR_UUID = "12345678-1234-5678-1234-56789abcdea3"

def handle_temp(_, data):
    temp = struct.unpack('<f', data)[0]
    print(f"Temperature: {temp:.2f} °C")

def handle_moist(_, data):
    moisture = struct.unpack('<h', data)[0]
    print(f"Moisture: {moisture}")

def handle_light(_, data):
    lux = struct.unpack('<f', data)[0]
    print(f"Light: {lux:.2f} lux")

async def main():
    print("Scanning for devices...")
    devices = await BleakScanner.discover()

    addr = None
    for d in devices:
        if d.name == DEVICE_NAME:
            addr = d.address
            break

    if not addr:
        print("Device not found")
        return

    async with BleakClient(addr) as client:
        print("Connected:", client.is_connected)

        await client.start_notify(TEMP_CHAR_UUID, handle_temp)
        await client.start_notify(MOIST_CHAR_UUID, handle_moist)
        await client.start_notify(LIGHT_CHAR_UUID, handle_light)

        print("Subscribed. Listening...\n")
        while True:
            await asyncio.sleep(1)

asyncio.run(main())
