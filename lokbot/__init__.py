import logging.handlers
import pathlib
import sys

from loguru import logger

project_root = pathlib.Path(__file__).parent.parent

builtin_logger = logging.getLogger(__name__)
builtin_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_channel = logging.handlers.TimedRotatingFileHandler(
    project_root.joinpath('builtin_logger.log'),
    interval=1,
    when='D',
    backupCount=1,
)
file_channel.setFormatter(formatter)

builtin_logger.addHandler(file_channel)

logger.remove()
logger.add(project_root.joinpath('loguru.log'), rotation='1 day', retention=2)
logger.add(sys.stdout, colorize=True)
