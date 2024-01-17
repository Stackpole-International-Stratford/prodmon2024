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

        self.connected = False
        self.frequency = frequency
        self.next_read = time.time()
        self.data_dir = data_dir


    def poll(self):
        if not self.is_connected():
            return

        timestamp = int(time.time())
        if self.next_read < timestamp:
            # increment now so it doesn't get missed
            self.next_read = timestamp + self.frequency

            for filepath in glob.iglob(self.data_dir + '*.dat'):
                self.logger.info(f'Found {filepath}')
                with open(filepath, "r", encoding="utf-8") as file:
                    result = True
                    for line in file:
                        result = result and self.handle_data(line) # all results must be true to delete file
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
        client.on_publish =  self.on_publish
        client.connect(self.ip, self.port)
        client.loop_start()
        return client

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.logger.info('Connected to MQTT Broker!')
        else:
            self.logger.info(f'Failed to connect, return code {rc}\n')

    def on_disconnect(self, client, userdata, rc):

        self.logger.warning(f'Disconnected with result code: {rc}')
        self.connected = False
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
            reconnect_delay = min(reconnect_delay, self.MAX_RECONNECT_DELAY)
            self.reconnect_count += 1
        self.logger.error(f'Reconnect failed after {self.reconnect_count} attempts. Exiting...')

    def handle_data(self, data):
        if not self.client.is_connected():
            return False

        try:
            entry_type, entry = data.split(':',1)
            
            topic = f'test/{entry_type}'

            ret = self.client.publish(topic=topic, payload=entry, qos=2)
            ret.wait_for_publish()
            self.logger.debug(f'{self.name}: {data}')
            return True
        except Exception as err:
            self.logger.error(f'{err}. Failed to send msg')

    def on_publish(self, client, userdata, mid):
        print(userdata, mid)

class MySQL_Target(Target):
    def __init__(self, name, data_dir, dbconfig, frequency, logger):
        super().__init__(name, None, None, data_dir, frequency, logger)
        self.dbconfig = dbconfig
        self.connection = False
        self.last_failed_connection_attempt = 0

    def is_connected(self):
        if self.connection:
            if self.connection.is_connected():
                return True
        # otherwise we are not connected.
        try:
            now = time.time()
            self.logger.info(f'Not connected to mysql server... reconnecting {now}')  
            self.connection= mysql.connector.connect(**self.dbconfig)
            self.last_failed_connection_attempt = 0
            return True

        except (mysql.connector.Error, IOError) as err:
            self.logger.error(f'Mysql connection failed: {err}')
            self.last_failed_connection_attempt = now
            return False                
        

    def handle_data(self, data):
        if self.is_connected():
            self.logger.debug(f'{self.name}: {data}')
            cursor = self.connection.cursor()
            entry_type, entry = data.split(':',1)
            entry = json.loads(entry)
            self.logger.debug(f'Handling data: {data}')

            if entry_type == 'PING':
                sql  =  'INSERT INTO prodmon_ping (Name, Timestamp) '
                sql += f'VALUES("{entry.get("name")}", {entry.get("timestamp")}) '
                sql +=  'ON DUPLICATE KEY UPDATE '
                sql += f'Name="{entry.get("name")}", Timestamp={entry.get("timestamp")};'

            elif entry_type == "COUNTER":
                sql  =  'INSERT INTO GFxPRoduction (Machine, Part, PerpetualCount, TimeStamp, Count) '
                sql += f'VALUES ("{entry.get("asset")}", "{entry.get("part")}", {entry.get("perpetualcount")}, '
                sql += f'{entry.get("timestamp")}, {entry.get("count")});'

            elif entry_type == "REJECT":
                sql  =  'INSERT INTO GFxPRoduction '
                sql +=  '(Machine, Part, PerpetualCount, TimeStamp, Count) '
                sql += f'VALUES("{entry.get("asset")}", '  
                sql += f'"{entry.get("part")}", '
                sql += f'{entry.get("perpetualcount")}, ' 
                sql += f'{entry.get("timestamp")}, ' 
                sql += f'{entry.get("count")});'
                sql +=  'INSERT INTO prodmon_prod_rejects '
                sql +=  '(GFxPRoduction_id, Reject_Reason) '
                sql +=  'VALUES (LAST_INSERT_ID(), '
                sql += f'"{entry.get("reason")}");'

            else: 
                raise NotImplementedError(f'Entry Type {entry_type} Not Implemented')

            try:
                cursor.execute(sql, multi=True)
                self.connection.commit()
                cursor.close()
                return True

            except Exception as e:
                self.logger.error(f'An error occured writing to the database:{e}')
                return False

