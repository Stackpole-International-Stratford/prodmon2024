import time
import yaml
import sys
import os
import random

from pylogix import PLC
from loguru import logger
from paho.mqtt import client as mqtt_client

from devices import PylogixDevice
from tags import PingTag

# used by mqtt broker on_connect()
broker = 'pmdsdata12'
port = 1883
topic = "python/mqtt"
client_id = f'python-mqtt-{random.randint(0, 1000)}'
# username = 'emqx'
# password = 'public'


# used by mqtt broker on_disconnect()
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60
FLAG_EXIT = False



TAG = 'Program:MainProgram.ProdCount.ACC'
PLC_IP = '10.4.43.103'

def read_config_file(config_key=None):
    if len(sys.argv) == 2:
        config_path = f'./configs/{sys.argv[1]}.yml'
    else:
        config_path = f'/etc/prodmon/{config_key}.config'

    logger.info(f'Getting config from {config_path}')

    if not os.path.exists(config_path):
        logger.exception(f'Config file not found! {config_path}')
        raise ValueError(f'Config file not found! {config_path}')

    with open(config_path, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    return config



def handle_update(value, mqtt_client):
    print('\n', value ,end = "")
    msg = f"Value: {value}"
    result = mqtt_client.publish(topic, msg)
    # result: [0, 1]
    status = result[0]
    if status == 0:
        logger.info(f"Send `{msg}` to topic `{topic}`")
    else:
        logger.info(f"Failed to send message to topic {topic}")




def connect_mqtt():

    broker = 'pmdsdata12'
    port = 1883
    topic = "test"
    client_id = f'python-mqtt-{random.randint(0, 1000)}'
    # username = 'emqx'
    # password = 'public'

    def on_connect(client, userdata, flags, rc):
        if rc == 0:
            logger.info("Connected to MQTT Broker!")
        else:
            logger.info("Failed to connect, return code %d\n", rc)

    # Set Connecting Client ID
    client = mqtt_client.Client(client_id)
    # client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


def on_disconnect(client, userdata, rc):
    logger.info("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logger.info("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logger.info("Reconnected successfully!")
            return
        except Exception as err:
            logger.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logger.info("Reconnect failed after %s attempts. Exiting...", reconnect_count)
    global FLAG_EXIT
    FLAG_EXIT = True







@logger.catch
def main():
    devices = []
    config = read_config_file()

    for device in config.get('devices'):
        print(device)

        name = device.get('name', None)
        ip = device.get('ip', None)
        frequency = device.get('frequency', 1)

        driver = device.get('driver', None)

        if driver == 'pylogix':
            slot = device.get('processor_slot', 0)
            device_entry = PylogixDevice(name, ip, frequency, slot)

        elif driver == 'modbus':
            raise NotImplementedError
            # device_entry = ModbusDevice(name, ip, frequency)

        for tag in device['tags']:
            device_entry.add_data_point(tag)


        devices.append(device_entry)


    while True:
        for device in devices:
            device.poll_tags()




    mqtt_client = connect_mqtt()
    
    next_read= time.time()
    frequency = 1
    last_value = 0
    with PLC() as comm:
        comm.IPAddress = config.get('PLC_IP')
        while True:
            timestamp = time.time()
            if timestamp >next_read :
                # increment now so it doesn't get missed
                next_read = timestamp + frequency
                ret = comm.Read(TAG)
                value = ret.Value
                if value > last_value:
                    handle_update(value, mqtt_client)
                    last_value = value
                next_read = timestamp + frequency
            print('.' ,end = "")
            time.sleep(.5)






if __name__ == "__main__":

    main()


