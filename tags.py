from abc import ABC, abstractmethod
import sys
import time
import json

from loguru import logger

SQL_DIRECTORY = 'temp/'

class Tag(ABC):

    def __init__(self, parent, address, frequency):
        self.parent = parent
        self.address = address
        self.type = None
        self.frequency = frequency
        self.next_read = time.time()
        self.last_value = None

    @abstractmethod
    def poll(self):
        pass

    @abstractmethod
    def format_output(self):
        pass


class PingTag(Tag):
    def __init__(self, parent, name, address, frequency):
        super().__init__(parent, address, frequency)
        self.type = 'ping'
        self.name = name

    def poll(self):
        timestamp = int(time.time())
        if self.next_read < timestamp:
            # increment now so it doesn't get missed
            self.next_read = timestamp + self.frequency

            value, error_flag = self.parent.read(self.address)
            if error_flag:
                return

            entry = self.format_output(timestamp)
            logger.debug(entry)
            
            sys.stdout.flush()
            file_path = f'{SQL_DIRECTORY}{str(timestamp)}.dat'
            with open(file_path, "a+") as file:
                file.write(entry)

    def format_output(self, timestamp):
        data = {"timestamp":timestamp,
                "name": self.name}
        return f'PING:{json.dumps(data)}'

class CounterTag(Tag):

    def __init__(self, parent, address, scale, frequency, machine, part_number_text_tag, part_number_index_tag, part_dict):
        super().__init__(parent, address, frequency)
        self.type = 'counter'
        self.db_machine_data = machine
        self.scale = scale
        if part_number_text_tag:
            self.part_number_tag = part_number_text_tag
        elif part_number_index_tag:
            self.part_number_tag = part_number_index_tag
            self.part_dict = part_dict

    def poll(self):
        timestamp = int(time.time())
        if self.next_read < timestamp:
            # increment now so it doesn't get missed
            self.next_read = timestamp + self.frequency

            tags, error_flag = self.parent.read([self.address, self.part_number_tag])
            if error_flag:
                return
            count = tags[0].Value
            count *= self.scale

            part = tags[1].Value
            if hasattr(self, 'part_dict'):
                part = self.part_dict.get(part, None)
                if not part:
                    logger.error(f'Part not defined: {tags[1].Value}:{self.part_dict}')
            
            # last_value is 0 or Null
            if not self.last_value:
                if self.last_value == 0:
                    logger.info(f'Counter Rolled over: Successfully read {self.parent.name}:{self.address} ({part}:{count})')
                else:
                    logger.info(f'First pass through: Successfully read {self.parent.name}:{self.address} ({part}:{count})')
                self.last_value = count
                return

            # no change
            if not count > self.last_value:
                return

            # create entry for new values
            sys.stdout.flush()
            file_path = f'{SQL_DIRECTORY}{str(timestamp)}.dat'
            with open(file_path, "a+") as file:

                for part_count in range(self.last_value + 1, count + 1):
                    entry = self.format_output(part_count, part, int(timestamp))
                    logger.debug(f'Create enrty for {self.db_machine_data} ({part}:{part_count})')
                    file.write(entry)
                    self.last_value = part_count

    def format_output(self, counter, part, timestamp):
        # create entry for new value
        data = {
            "asset": self.db_machine_data,
            "part": part,
            "timestamp": timestamp,
            "perpetualcount": counter,
            "count": 1,
        }
        return f'COUNTER:{json.dumps(data)}'



class DataTag(Tag):

    def __init__(self, parent, address, scale, frequency, db_table, machine, part_number):
        raise NotImplementedError('Data Tags are not implemented')
        super().__init__(parent, address, scale, frequency, db_table)
        self.type = 'data'

    def poll(self):
        pass

