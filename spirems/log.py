#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import logging


def get_logger(name: str = "default"):
    logger = logging.getLogger(name)
    formatter = logging.Formatter('[%(levelname)s] [%(name)s] %(asctime)s - %(message)s')
    f_handler = logging.FileHandler('log.txt')
    f_handler.setFormatter(formatter)
    formatter = logging.Formatter('[%(levelname)s] [%(name)s] %(message)s')
    s_handler = logging.StreamHandler()
    s_handler.setFormatter(formatter)
    logger.setLevel(level=logging.DEBUG)
    logger.addHandler(s_handler)
    logger.addHandler(f_handler)
    return logger
