import time
import yaml
import sys
import os
from pylogix import PLC
from loguru import logger


TAG = 'Program:MainProgram.ProdCount.ACC'
PLC_IP = '10.4.43.103'

def read_config_file(config_key=None):
    if len(sys.argv) == 2:
        config_path = f'./configs/{sys.argv[1]}.yml'
    else:
        config_path = f'/etc/prodmon/{config_key}.config'

    logger.info(f'Getting config from {config_path}')

    if not os.path.exists(config_path):
        logger.exception(f'Config file not found! {config_path}')
        raise ValueError(f'Config file not found! {config_path}')

    with open(config_path, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)

    return config

@logger.catch
def main():

    config = read_config_file()

    next_read= time.time()
    frequency = 1
    last_value = 0
    with PLC() as comm:
        comm.IPAddress = config.get('PLC_IP')
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


