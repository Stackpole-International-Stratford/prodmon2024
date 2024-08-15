from abc import ABC, abstractmethod
import sys
import time
import json

from loguru import logger

class Tag(ABC):

    def __init__(self, parent, address, frequency):
        self.parent = parent
        self.address = address
        self.type = None
        self.frequency = frequency
        self.next_read = time.time()
        self.last_value = None
        self.data_dir = None
        self.line = 'default'

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
        import pdb; pdb.set_trace()
        timestamp = int(time.time())
        if self.next_read < timestamp:
            # increment now so it doesn't get missed
            self.next_read = timestamp + self.frequency

            values, error_flag = self.parent.read(self.address)
            if error_flag:
                return

            entry = self.format_output(timestamp)
            logger.info(f'PING {self.name} @ {timestamp}')
            sys.stdout.flush()
            file_path = f'{self.data_dir}{str(timestamp)}.dat'
            with open(file_path, "a+") as file:
                file.write(entry)

    def format_output(self, timestamp):
        data = {
            'organization': self.organization,
            'site': self.site,
            'line': self.line,
            'asset': self.machine,
            'timestamp' :timestamp,
            }
        return f'PING:{json.dumps(data)}\n'


class CounterTag(Tag):

    def __init__(self, parent, address, scale, frequency, machine, part=None, part_number_tag=None, part_dict=None):
        super().__init__(parent, address, frequency)
        self.type = 'counter'
        self.db_machine_data = machine
        self.scale = scale
        # used to set a fixed part number in config
        self.part = part
        # used to get the part number tag from the device (direct read)
        self.part_number_tag = part_number_tag
        # used to get the part number from a dictionary using a tag as an index 
        self.part_dict = part_dict

    def poll(self):
        timestamp = int(time.time())
        if self.next_read < timestamp:
            # increment now so it doesn't get missed
            self.next_read = timestamp + self.frequency

            # build the listof tags to check
            taglist = [self.address]
            # if self.part is defined, part number is hard coded
            # else, add the part_number_tag to the read list
            if not self.part: 
                taglist.append(self.part_number_tag)

            values, error_flag = self.parent.read(taglist)
            if error_flag:
                return
            # first return is the counter
            count = values[0]
            count *= self.scale

            # if a second value returned, it is the part number tag
            if len(values) == 2:
                part = values[1]
                # if we have a part_dict, then dereference the part number
                if self.part_dict:
                    part = self.part_dict.get(part, None)
                    if not part:
                        logger.error(f'Part not defined: {values[1]}:{self.part_dict}')
            else:
                part = self.part

            # last_value is 0 or Null
            if not self.last_value:
                if self.last_value == 0:
                    logger.debug(f'Counter Rolled over: Successfully read {self.parent.name}:{self.address} ({part}:{count})')
                else:
                    logger.info(f'First pass through: Successfully read {self.parent.name}:{self.address} ({part}:{count})')
                self.last_value = count
                return

            # no change
            if not count > self.last_value:
                self.last_value = count # if counter goes backward, reset last value 
                return

            # create entry for new values
            sys.stdout.flush()
            file_path = f'{self.data_dir}{str(timestamp)}.dat'
            with open(file_path, "a+") as file:
                for part_count in range(self.last_value + 1, count + 1):
                    entry = self.format_output(part_count, part, int(timestamp))
                    logger.info(f'Create enrty for {self.db_machine_data} ({part}:{part_count})')
                    file.write(entry)
                    self.last_value = part_count

    def format_output(self, counter, part, timestamp):
        # create entry for new value
        data = {
            'organization': self.organization,
            'site': self.site,
            "line": self.line,
            'asset': self.db_machine_data,
            'part': part,
            'timestamp': timestamp,
            'perpetualcount': counter,
            'count': 1,
        }
        return f'COUNTER:{json.dumps(data)}\n'


class RejectTag(CounterTag):
    def __init__(self, parent, address, scale, frequency, machine, part=None, part_number_tag=None, part_dict=None):
        machine = f'{machine}'
        super().__init__(parent, address, scale, frequency, machine, part, part_number_tag, part_dict)
        self.type = 'reject'
        self.reason = None

    def format_output(self, counter, part, timestamp):
        # create entry for new value
        data = {
            'organization': self.organization,
            'site': self.site,
            "line": self.line,
            "asset": self.db_machine_data,
            "part": part,
            "timestamp": timestamp,
            "perpetualcount": counter,
            "count": 1,
            "reason": self.reason,
        }
        return f'REJECT:{json.dumps(data)}\n'

    

class DataTag(Tag):

    def __init__(self, parent, address, scale, frequency, machine, part=None, part_number_tag=None, part_dict=None):
        super().__init__(parent, address, frequency)
        self.db_machine_data = machine
        self.scale = scale
        # used to set a fixed part number in config
        self.part = part
        # used to get the part number tag from the device (direct read)
        self.part_number_tag = part_number_tag
        # used to get the part number from a dictionary using a tag as an index 
        self.part_dict = part_dict

    def poll(self):
        # pass
        timestamp = int(time.time())
        if self.next_read < timestamp:
            # increment now so it doesn't get missed
            self.next_read = timestamp + self.frequency

            # build the listof tags to check
            taglist = [self.address]
            # if self.part is defined, part number is hard coded
            # else, add the part_number_tag to the read list
            if not self.part: 
                taglist.append(self.part_number_tag)

            values, error_flag = self.parent.read(taglist)
            if error_flag:
                return
            # first return is the process value
            process_value = values[0]
            process_value *= self.scale

            # if a second value returned, it is the part number tag
            if len(values) == 2:
                part = values[1]
                # if we have a part_dict, then dereference the part number
                if self.part_dict:
                    part = self.part_dict.get(part, None)
                    if not part:
                        logger.error(f'Part not defined: {values[1]}:{self.part_dict}')
            else:
                part = self.part

            # last_value is 0 or Null
            if self.last_value is None:
                logger.info(f'First pass through: Successfully read {self.parent.name}:{self.address} ({part}:{process_value})')
                self.last_value = process_value
                return

            # no change
            if process_value == self.last_value:
                return

            # create entry for new values
            sys.stdout.flush()
            file_path = f'{self.data_dir}{str(timestamp)}.dat'
            with open(file_path, "a+") as file:
                entry = self.format_output(process_value, part, int(timestamp))
                logger.info(f'Create enrty for {self.db_machine_data} (Process Value:{process_value})')
                file.write(entry)
                self.last_value = process_value

    def format_output(self, process_value, part, timestamp):
        # create entry for new value
        data = {
            'organization': self.organization,
            'site': self.site,
            "line": self.line,
            'asset': self.db_machine_data,
            'part': part,
            'timestamp': timestamp,
            'name': self.name,
            'process_value': process_value,
        }
        return f'DATA:{json.dumps(data)}\n'
