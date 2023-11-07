import time

from pylogix import PLC
from loguru import logger


TAG = 'Program:MainProgram.ProdCount.ACC'
PLC_IP = '10.4.43.103'


@logger.catch
def main():
    next_read= time.time()
    frequency = 1
    last_value = 0
    with PLC() as comm:
        comm.IPAddress = PLC_IP
        

        while True:
            timestamp = time.time()
            if timestamp >next_read :
                # increment now so it doesn't get missed
                next_read = timestamp + frequency
                ret = comm.Read(TAG)
                value = ret.Value
                if value > last_value:

                    print('\n', value ,end = "")
                    last_value = value
                next_read = timestamp + frequency
            print('.' ,end = "")
            time.sleep(.5)




if __name__ == "__main__":
    main()


