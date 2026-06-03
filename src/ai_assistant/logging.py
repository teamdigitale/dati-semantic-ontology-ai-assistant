# coding: utf-8

import logging
import os

__all__ = (
    "logger",
    "set_log_file",
)

LOG_FORMAT = logging.Formatter('%(asctime)s [%(levelname)s]: %(message)s')
default_handler = logging.StreamHandler()
default_handler.setFormatter(LOG_FORMAT)

logger = logging.getLogger('ai_assistant')
logger.setLevel(logging.WARN)
logger.addHandler(default_handler)


def set_log_file(path: str | os.PathLike[str], mode: str = "a"):
    handler = logging.FileHandler(path, mode)
    handler.setFormatter(LOG_FORMAT)
    for h in logger.handlers:
        logger.removeHandler(h)
    logger.addHandler(handler)

