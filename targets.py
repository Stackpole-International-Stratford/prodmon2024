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
                result = True
                for line in file:
                    data = line #json.loads(line)
                    result = result and self.handle_data(data) # all results must be true to delete file
            if result:
                os.remove(filepath)

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
        self.logger.debug(f'{self.name}: {data}')
        return True


class MySQL_Target(Target):
    def __init__(self, name, data_dir, dbconfig, frequency, logger):
        super().__init__(name, None, None, data_dir, frequency, logger)
        self.dbconfig = dbconfig
        self.connection = False

    def connected(self):
        if self.connection:
           if self.connection.is_connected():
               return True

        CONNECT_ATTEMPTS = 3
        CONNECT_DELAY = 2

        attempt = 1
        # Implement a reconnection routine
        while attempt < CONNECT_ATTEMPTS:
            try:
                self.connection= mysql.connector.connect(**self.dbconfig)
                return True

            except (mysql.connector.Error, IOError) as err:
                if (CONNECT_ATTEMPTS is attempt):
                    # Attempts to reconnect failed; returning None
                    self.logger.info(f'Failed to connect, exiting without a connection: {err}')
                    raise
                self.logger.info(f'Connection failed: {err}. Retrying ({attempt}/{CONNECT_ATTEMPTS})...')
                # progressive reconnect delay
                time.sleep(CONNECT_DELAY ** attempt)
                attempt += 1
        

    def handle_data(self, data):
        if self.connected():
            self.logger.debug(f'{self.name}: {data}')
            cursor = self.connection.cursor()
            entry_type, entry = data.split(':',1)
            entry = json.loads(entry)

            if entry_type == 'PING':
                sql =   'INSERT INTO prodmon_ping (Name, Timestamp) '
                sql += f'VALUES("{entry.get("name")}", {entry.get("timestamp")}) '
                sql +=  'ON DUPLICATE KEY UPDATE '
                sql += f'Name="{entry.get("name")}", Timestamp={entry.get("timestamp")};'

            elif entry_type == "COUNTER":
                sql =   'INSERT INTO GFxPRoduction (Machine, Part, PerpetualCount, TimeStamp, Count) '
                sql += f'VALUES ("{entry.get("asset")}", "{entry.get("part")}", {entry.get("perpetualcount")}, '
                sql += f'{entry.get("timestamp")}, {entry.get("count")});'

            else: 
                raise NotImplementedError(f'Entry Type {entry_type} Not Implemented')

            try:
                cursor.execute(sql)
                self.connection.commit()
                return True

            except Exception as e:
       # By this way we can know about the type of error occurring
                self.logger.error(f'The error is: {e}')
                return False

    def execute_sql(self, post_config):
        # TODO:  Check if sql file exists before opening mysql connection
        # if not os.path.exists(sqldir + '*.sql'):
        #     return

        if self.connected():


            for filepath in glob.iglob(self.data_dir + '*.dat'):
                self.logger.info(f'Found {filepath}')
                with open(filepath, "r", encoding="utf-8") as file:
                    for line in file:
                        sql = self.parse_line(line)
                os.remove(filepath)

            cursor.close()
