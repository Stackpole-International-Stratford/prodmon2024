from abc import ABC, abstractmethod
import time
from loguru import logger

class Tag(ABC):

    def __init__(self, parent, address, scale, frequency):
        self.parent = parent
        self.address = address
        self.type = None
        self.scale = scale
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
        super().__init__(parent, address, 1, frequency)
        self.type = 'ping'
        self.name = name

    def poll(self):
        timestamp = time.time()
        if self.next_read < timestamp:
            # increment now so it doesn't get missed
            self.next_read = timestamp + self.frequency

            value, error_flag = self.parent.read(self)
            if error_flag:
                return
            logger.info(self.format_output(timestamp, value))

    def format_output(self, timestamp, value):
        output = f'Ping {self.name}({value}) @ {timestamp}'
        return output
