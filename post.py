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
            dbconfig = target.get('dbconfig', None)
            device_entry = MySQL_Target(name, data_dir, dbconfig, frequency, logger)

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
