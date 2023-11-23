import os
import sys
import yaml

from loguru import logger

def config_default(config_dict, key, default):
    if key not in config_dict:
        config_dict[key] = default

def read_config_file(config_key=None):
    if len(sys.argv) == 2:
        config_path = f'{sys.argv[1]}'
    else:
        config_path = f'/etc/prodmon/{config_key}.config'

    logger.info(f'Getting config from {config_path}')

    if not os.path.exists(config_path):
        logger.exception(f'Config file not found! {config_path}')
        raise ValueError(f'Config file not found! {config_path}')

    with open(config_path, 'r') as file:
        config = yaml.load(file, Loader=yaml.FullLoader)
    return config

def get_logger():
    
    log_level = "INFO"
    if os.environ["DEBUG"]:
        log_level = "DEBUG"

    log_level = os.environ.get("LOG_LEVEL", default=log_level)

    # Remove and reconfigure default sys.error logger
    logger.remove(0)
    logger.add(sys.stderr, level=log_level)

    # configure file logger
    if os.environ.get("DEBUG", default=False):
        logger.add('templogs/prodmon-collect.log', level=log_level)
    else:
        logger.add('/var/log/prodmon-collect.log', rotation="10 Mb", level=log_level)

    logger.info(f'Logging set to {log_level}')
    return logger
