import json
import logging.handlers
import os
import pathlib
import sys

from loguru import logger

project_root = pathlib.Path(__file__).parent.parent

project_root.joinpath('data').mkdir(exist_ok=True)


def load_config():
    os.chdir(project_root)

    if os.path.exists('config.json'):
        return json.load(open('config.json'))

    if os.path.exists('config.example.json'):
        return json.load(open('config.example.json'))

    return {}


config = load_config()

# region socket-io related loggers

socf_logger = logging.getLogger(f'{__name__}.socf')
sock_logger = logging.getLogger(f'{__name__}.sock')
socc_logger = logging.getLogger(f'{__name__}.socc')

if config.get('socketio').get('debug'):
    socf_logger.setLevel(logging.DEBUG)
    sock_logger.setLevel(logging.DEBUG)
    socc_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

socf_file_channel = logging.handlers.TimedRotatingFileHandler(
    project_root.joinpath('data/socf.log'), interval=1, when='H', backupCount=48
)
socf_file_channel.setFormatter(formatter)
socf_logger.addHandler(socf_file_channel)
sock_file_channel = logging.handlers.TimedRotatingFileHandler(
    project_root.joinpath('data/sock.log'), interval=1, when='H', backupCount=48
)
sock_file_channel.setFormatter(formatter)
sock_logger.addHandler(sock_file_channel)
socc_file_channel = logging.handlers.TimedRotatingFileHandler(
    project_root.joinpath('data/socc.log'), interval=1, when='H', backupCount=48
)
socc_file_channel.setFormatter(formatter)
socc_logger.addHandler(socc_file_channel)

# endregion

logger.remove()
logger.add(project_root.joinpath('data/main.log'), rotation='1 hour', retention=48)
logger.add(sys.stdout, colorize=True)
