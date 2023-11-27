import time
import glob
import os
import random
from time import sleep

from targets import Mqtt_Target, MySQL_Target


from shared import get_logger, read_config_file
logger = get_logger('post')


def read_config(key):
    config = read_config_file(key)
    targets = []
    for target in config.get('targets'):
        name = target.get('name', None)

        data_dir = target.get('data_dir', None)
        frequency = target.get('frequency', 1)

        driver = target.get('driver', None)

        if driver == 'mqtt':
            ip = target.get('ip', None)
            port = target.get('port', None)
    
            client_id = target.get('client_id', None)

            # def __init__(self, name, ip, data_dir, frequency, port=None, client_id=None):
            device_entry = Mqtt_Target(name, ip, data_dir, frequency, logger, port=port, client_id=client_id)

        elif driver == 'mysql':
            ip = target.get('ip', None)
            port = target.get('port', None)
            device_entry = MySQL_Target(name, ip, data_dir, frequency, logger, port=port)

        else:
            raise NotImplementedError(f'Target {name} driver ({driver}) not implemented')

        targets.append(device_entry)
    return targets

@logger.catch
def main():
    targets = read_config('post')

    # while not FLAG_EXIT:
    while True:
        for target in targets:
            target.poll()
            time.sleep(.2)

if __name__ == "__main__":
    main()









# used by mqtt broker on_disconnect()
FIRST_RECONNECT_DELAY = 1
RECONNECT_RATE = 2
MAX_RECONNECT_COUNT = 12
MAX_RECONNECT_DELAY = 60
FLAG_EXIT = False



def connect_mqtt():
    broker = 'pmdsdata12'
    port = 1883
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
    logger.warning("Disconnected with result code: %s", rc)
    reconnect_count, reconnect_delay = 0, FIRST_RECONNECT_DELAY
    while reconnect_count < MAX_RECONNECT_COUNT:
        logger.warning("Reconnecting in %d seconds...", reconnect_delay)
        time.sleep(reconnect_delay)

        try:
            client.reconnect()
            logger.warning("Reconnected successfully!")
            return
        except Exception as err:
            logger.error("%s. Reconnect failed. Retrying...", err)

        reconnect_delay *= RECONNECT_RATE
        reconnect_delay = min(reconnect_delay, MAX_RECONNECT_DELAY)
        reconnect_count += 1
    logger.error("Reconnect failed after %s attempts. Exiting...", reconnect_count)
    global FLAG_EXIT
    FLAG_EXIT = True

mqtt_client = connect_mqtt()