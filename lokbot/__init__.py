import logging
import pathlib

from loguru import logger

project_root = pathlib.Path(__file__).parent.parent

builtin_logger = logging.getLogger(__name__)
builtin_logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

file_channel = logging.FileHandler(project_root.joinpath('builtin_logger.log'))
file_channel.setFormatter(formatter)

builtin_logger.addHandler(file_channel)

logger.add(project_root.joinpath('loguru.log'))
