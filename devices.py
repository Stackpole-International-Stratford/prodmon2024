from abc import ABC, abstractmethod
import time
from loguru import logger
from pylogix import PLC

from tags import PingTag

class Device(ABC):

    def __init__(self, name, ip, frequency):
        self.name = name
        self.ip = ip
        self.frequency = frequency
        self.tag_list = []

    def add_data_point(self, tag):
        self.tag_list.append(tag)

    def poll_tags(self):
        for tag in self.tag_list:
            tag.poll()

    # @abstractmethod
    # def process_counter_tag(self, tag):
    #     pass

    @abstractmethod
    def read(self, tag):
        pass


class PylogixDevice(Device):

    def __init__(self, name, ip, frequency, slot):
        super().__init__(name, ip, frequency)
        self.driver = "pylogix"
        self.processor_slot = slot
        self.comm = PLC(ip_address=self.ip, slot=self.processor_slot)

    def add_data_point(self, tag):
        tag_type = tag.get('type', None)
        frequency = tag.get('frequency', 0)
        frequency = max(self.frequency, frequency)
        tag_name = tag.get('tag', None)
        parent = self

        if tag_type == 'counter':
            raise NotImplementedError
            # scale = tag.get('scale', 1)
            # machine = tag.get('machine', None)
            # part_number = tag.get('part_number', None)
            # new_tag_object = CounterTag(parent, tag_name, scale, frequency, db_table, machine, part_number)

        elif tag_type == 'ping':
            name = tag.get('name', None)
            new_tag_object = PingTag(parent, name, tag_name, frequency)

        elif tag_type == 'data':
            raise NotImplementedError
            # name = tag.get('name', None)
            # strategy = tag.get('strategy', None)
            # new_tag_object = DataTag(parent, tag_name, scale, db_table, name, strategy)

        else:
            raise NotImplementedError

        super().add_data_point(new_tag_object)

    def read(self, tag):
        error_flag = False
        ret = self.comm.Read(tag.address)

        if ret.Status != "Success":
            logger.info(f'Failed to read {self.name}:{tag.address} ({ret.Status})')
            error_flag = True
        else:
            logger.debug(f'Successfully read {self.name}:{tag.address} ({ret.Value})')
        return ret.Value, error_flag


class ModbusDevice(Device):

    def __init__(self, name, ip, frequency):
        super().__init__(name, ip, frequency)
        self.driver = "modbus"
        # self.comm = ModbusClient(host=ip, auto_open=True, auto_close=True)

    def add_data_point(self, tag):
        tag_type = tag.get('type', None)
        register = tag.get('register', None)
        scale = tag.get('scale', 1)
        frequency = tag.get('frequency', 0)
        frequency = max(self.frequency, frequency)
        db_table = tag.get('table', None)
        parent = self

        if tag_type == 'ADAM_counter':
            raise NotImplementedError
            # machine = tag.get('machine', None)
            # part_number = tag.get('part_number', None)
            # tag_object = CounterTag(parent, register, scale, frequency, db_table, machine, part_number)

        elif tag_type == 'ping':
            name = tag.get('name', None)
            tag_object = PingTag(parent, name, register, frequency, db_table)

        elif tag_type == 'data':
            raise NotImplementedError
            # name = tag.get('name', None)
            # strategy = tag.get('strategy', None)
            # tag_object = DataTag(parent, None, frequency, db_table, strategy)

        super().add_data_point(tag_object)

    def read(self, tag):
        error_flag = False
        count = None
        regs = self.comm.read_holding_registers(tag.address, 2)

        if regs:
            count = regs[0] + (regs[1] * 65536)
            logger.debug(f'Successfully read {self.name}:{tag.address} ({count})')
        else:
            error_flag = True
            count = None
            logger.info(f'Failed to read {self.name}:{tag.address}')

        return count, error_flag
