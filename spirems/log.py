#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import logging
import os
from datetime import datetime


log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
LOGER_NAMES = dict()


def get_logger(name: str = "default"):
    if name not in LOGER_NAMES:
        logger = logging.getLogger(name)
        formatter = logging.Formatter('[%(levelname)s] [%(name)s] %(asctime)s - %(message)s')
        current_time = datetime.now()
        formatted_time = current_time.strftime("log_%Y_%m_%d.txt")
        f_handler = logging.FileHandler(os.path.join(log_dir, formatted_time))
        f_handler.encoding = 'utf-8'
        f_handler.setFormatter(formatter)
        formatter = logging.Formatter('[%(levelname)s] [%(name)s] %(message)s')
        s_handler = logging.StreamHandler()
        s_handler.encoding = 'utf-8'
        s_handler.setFormatter(formatter)
        logger.setLevel(level=logging.DEBUG)
        logger.addHandler(s_handler)
        logger.addHandler(f_handler)
        LOGER_NAMES[name] = logger
    return LOGER_NAMES[name]
