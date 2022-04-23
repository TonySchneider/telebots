import sys
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s', stream=sys.stdout)


def get_logger(logger_name):
    return logging.getLogger(logger_name)