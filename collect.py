import time
import yaml
import sys
import os
import random
import time

from devices import PylogixDevice, ModbusDevice

from shared import get_logger, read_config_file
logger = get_logger('collect')

def read_config(key):
    devices = []
    config = read_config_file(key)

    for device in config.get('devices'):
        name = device.get('name', None)
        ip = device.get('ip', None)
        frequency = device.get('frequency', 1)
        data_dir = device.get('data_dir', None)
        driver = device.get('driver', None)

        if driver == 'pylogix':
            slot = device.get('processor_slot', 0)
            route = device.get('route', None)
            port = device.get('port', 44818)
            device_entry = PylogixDevice(name, ip, frequency, slot=slot, port=port, route=route)

        elif driver == 'modbus':
            port = device.get('port', 502)
            unit_id = device.get('unit_id', 1)
            device_entry = ModbusDevice(name, ip, frequency, port=port, unit_id=unit_id)

        device_entry.part = device.get('part', None)
        device_entry.data_dir = data_dir

        for tag in device['tags']:
            device_entry.add_data_point(tag)

        devices.append(device_entry)
    return devices


@logger.catch
def main():
    devices = read_config('collect')

    # while not FLAG_EXIT:
    while True:
        for device in devices:
            device.poll_tags()

        time.sleep(.5)

if __name__ == "__main__":

    main()


