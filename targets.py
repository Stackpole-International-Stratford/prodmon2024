from abc import ABC, abstractmethod
import glob
import os
import time
import json

from paho.mqtt import client as mqtt_client
import mysql.connector

from shared import get_logger


class Target(ABC):
    def __init__(self, name, ip, port, data_dir, frequency, logger):

        self.name = name
        self.logger = logger

        self.ip=ip
        self.port = port

        self.frequency = frequency
        self.data_dir = data_dir

    def poll(self):
        for filepath in glob.iglob(self.data_dir + '*.dat'):
            self.logger.info(f'Found {filepath}')
            with open(filepath, "r", encoding="utf-8") as file:
                for line in file:
                    data = json.loads(line)
                    self.handle_data(data)

    @abstractmethod
    def handle_data(self, data):
        pass


class Mqtt_Target(Target):
    def __init__(self, name, ip, data_dir, frequency, logger, port=None, client_id=None):
        if not port:
            port = 1883
        super().__init__(name, ip, port, data_dir, frequency, logger)

        if not client_id:
            client_id = f'mqtt-client-{name}'
        self.client_id = client_id

        self.reconnect_count = 0
        self.FIRST_RECONNECT_DELAY = 1
        self.RECONNECT_RATE = 2
        self.MAX_RECONNECT_COUNT = 12
        self.MAX_RECONNECT_DELAY = 60

        self.client = self.create_mqtt_client()

    def create_mqtt_client(self, username=None, password=None):
        client = mqtt_client.Client(self.client_id)
        if username and password:
            client.username_pw_set(username, password)
        client.on_connect = self.on_connect
        client.on_disconnect = self.on_disconnect
        client.loop_start()
        client.connect(self.ip, self.port)
        return client

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.logger.info('Connected to MQTT Broker!')
        else:
            self.logger.info(f'Failed to connect, return code {rc}\n')

    def on_disconnect(self, client, userdata, rc):
        self.logger.warning(f'Disconnected with result code: {rc}')
        reconnect_count, reconnect_delay = 0, self.FIRST_RECONNECT_DELAY
        while reconnect_count < self.MAX_RECONNECT_COUNT:
            self.logger.warning(f'Reconnecting in {reconnect_delay} seconds...')
            time.sleep(reconnect_delay)

            try:
                client.reconnect()
                self.logger.warning('Reconnected successfully!')
                return
            except Exception as err:
                self.logger.error(f'{err}. Reconnect failed. Retrying...')

            reconnect_delay *= self.RECONNECT_RATE
            reconnect_delay = min(self.RECONNECT_DELAY, self.MAX_RECONNECT_DELAY)
            self.reconnect_count += 1
        self.logger.error(f'Reconnect failed after {self.reconnect_count} attempts. Exiting...')

    def handle_data(self, data):
        self.logger.debug(f'{self.name}{data}')


class MySQL_Target(Target):
    def __init__(self, name, ip, data_dir, frequency, logger, port=None):
        if not port:
            port = 3306
        super().__init__(name, ip, port, data_dir, frequency, logger)

    def handle_data(self, data):
        self.logger.debug(f'{self.name}{data}')


    def execute_sql(self, post_config):
        dbconfig = post_config['dbconfig']
        sqldir = post_config['sqldir']

        # TODO:  Check if sql file exists before opening mysql connection
        # if not os.path.exists(sqldir + '*.sql'):
        #     return

        cnx = mysql.connector.connect(**dbconfig)
        cursor = cnx.cursor()

        for filepath in glob.iglob(sqldir + '*.sql'):
            self.logger.info(f'Found {filepath}')
            with open(filepath, "r", encoding="utf-8") as file:
                for line in file:
                    sql = line.strip()
                    self.logger.debug(f'Posting {sql} to database')
                    cursor.execute(sql)
            cnx.commit()
            os.remove(filepath)

        cursor.close()
        cnx.close()
