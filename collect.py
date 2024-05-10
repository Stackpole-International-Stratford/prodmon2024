import time
import yaml
import sys
import os
import random

import asyncio
from asyncua import Server

from slugify import slugify

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
async def main():
    devices = read_config('collect')

    # setup opc-ua server
    server = Server()
    logger.info('Starting OPC-UA server... may take a moment')
    await server.init()
    logger.info('OPC-UA server initalized')
    server.set_endpoint("opc.tcp://0.0.0.0:4840/test/async/")

    # set up our own namespace, not really necessary but should as spec
    uri = "http://pmdsdata12/test/"
    idx = await server.register_namespace(uri)


    for device in devices:
        device_name = slugify(device.name)
        print(device_name)
        device.opcua_object = await server.nodes.objects.add_object(idx, device_name)
        for tag in device.tag_list:
            if not tag.type == 'ping':
                node_name = slugify(getattr(tag, 'name', 'NoName'))
                tag.opcua_node = await device.opcua_object.add_variable(idx, node_name, 0)

    # while not FLAG_EXIT:
    async with server:
        while True:
            await asyncio.sleep(.1)
            for device in devices:
                device.poll_tags()
                for tag in device.tag_list:
                    if tag.update_opcua:
                        await tag.opcua_node.write_value(tag.last_value)

if __name__ == "__main__":

    asyncio.run(main(), debug=True)



