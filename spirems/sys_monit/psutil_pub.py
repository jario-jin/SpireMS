#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import psutil
import time
from spirems.log import get_logger
from spirems.publisher import Publisher
from spirems.msg_helper import def_msg


logger = get_logger('PsutilPub')


def cpu_monit():
    values = []
    cpu_cnt = psutil.cpu_count()
    # logger.debug("cpu_count: {}".format(cpu_cnt))
    cpu_percent = psutil.cpu_percent(interval=1)
    logger.debug("cpu_percent: {}".format(cpu_percent))
    values.append(cpu_percent)
    cpu_freq = psutil.cpu_freq(percpu=False)
    # logger.debug("cpu_freq: {}".format(cpu_freq))
    # logger.debug("cpu_freq.current: {}".format(cpu_freq.current))
    # logger.debug("cpu_freq.max: {}".format(cpu_freq.max))

    virtual_memory = psutil.virtual_memory()
    # logger.debug("virtual_memory: {}".format(virtual_memory))
    # logger.debug("virtual_memory.total: {}".format(virtual_memory.total / 1024 / 1024 / 1024))
    logger.debug("virtual_memory.available: {}".format(virtual_memory.available / 1024 / 1024 / 1024))
    values.append(virtual_memory.available / 1024 / 1024 / 1024)

    net_io_counters = psutil.net_io_counters()
    # logger.debug("net_io_counters: {}".format(net_io_counters))
    # logger.debug("net_io_counters.bytes_sent: {}".format(net_io_counters.bytes_sent / 1024 / 1024 / 1024))
    # logger.debug("net_io_counters.bytes_recv: {}".format(net_io_counters.bytes_recv / 1024 / 1024 / 1024))
    values.append(net_io_counters.bytes_sent / 1024 / 1024 / 1024)
    values.append(net_io_counters.bytes_recv / 1024 / 1024 / 1024)
    # logger.debug("net_io_counters.packets_sent: {}".format(net_io_counters.packets_sent))
    # logger.debug("net_io_counters.packets_recv: {}".format(net_io_counters.packets_recv))

    disk_usage = psutil.disk_usage('/')
    # logger.debug("disk_usage: {}".format(disk_usage))
    # logger.debug("disk_usage.total: {}".format(disk_usage.total / 1024 / 1024 / 1024))
    # logger.debug("disk_usage.free: {}".format(disk_usage.free / 1024 / 1024 / 1024))
    values.append(disk_usage.free / 1024 / 1024 / 1024)

    disk_io_counters = psutil.disk_io_counters(perdisk=False)
    # logger.debug("disk_io_counters: {}".format(disk_io_counters))
    # logger.debug("disk_io_counters.read_bytes: {}".format(disk_io_counters.read_bytes / 1024 / 1024 / 1024))
    # logger.debug("disk_io_counters.write_bytes: {}".format(disk_io_counters.write_bytes / 1024 / 1024 / 1024))
    values.append(disk_io_counters.read_bytes / 1024 / 1024 / 1024)
    values.append(disk_io_counters.write_bytes / 1024 / 1024 / 1024)
    # logger.debug("disk_io_counters.read_count: {}".format(disk_io_counters.read_count))
    # logger.debug("disk_io_counters.write_count: {}".format(disk_io_counters.write_count))

    # sensors_temperatures = psutil.sensors_temperatures()
    # logger.debug("sensors_temperatures: {}".format(sensors_temperatures))
    # logger.debug("sensors_temperatures.coretemp: {}".format(sensors_temperatures['coretemp'][0].current))
    # values.append(sensors_temperatures['coretemp'][0].current)
    return values


def a2rl_pub():
    pub = Publisher('/a2rl/monit', 'std_msgs::NumberMultiArray')

    while True:
        # time.sleep(1)
        msg_num = def_msg('std_msgs::NumberMultiArray')
        msg_num['data'] = cpu_monit()
        pub.publish(msg_num)


if __name__ == '__main__':
    a2rl_pub()
