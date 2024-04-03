#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import sys
import time
from spirems.subscriber import Subscriber


class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARK_CYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    RESET = '\033[0m'


last_net_out = 0
last_net_in = 0
last_disk_read = 0
last_disk_write = 0
last_time = 0


def callback_f(msg):
    global last_net_out, last_net_in, last_disk_read, last_disk_write, last_time
    sys.stdout.write(Color.GREEN + "\rCPU: {:.2f} %, ".format(msg['data'][0]) + Color.RESET)
    sys.stdout.write(Color.GREEN + "Memory: {:.2f} GB, ".format(msg['data'][1]) + Color.RESET)
    if last_net_out > 0:
        net_out = (msg['data'][2] - last_net_out) / (msg['timestamp'] - last_time)
        sys.stdout.write(Color.DARK_CYAN + "Net-Send: {:.1f} MB/s, ".format(net_out * 1024) + Color.RESET)
    last_net_out = msg['data'][2]
    if last_net_in > 0:
        net_in = (msg['data'][3] - last_net_in) / (msg['timestamp'] - last_time)
        sys.stdout.write(Color.DARK_CYAN + "Net-Recv: {:.1f} MB/s, ".format(net_in * 1024) + Color.RESET)
    last_net_in = msg['data'][3]
    sys.stdout.write(Color.BLUE + "Disk-Free: {:.1f} GB, ".format(msg['data'][4]) + Color.RESET)
    if last_disk_read > 0:
        disk_read = (msg['data'][5] - last_disk_read) / (msg['timestamp'] - last_time)
        sys.stdout.write(Color.PURPLE + "Disk-Read: {:.2f} MB/s, ".format(disk_read * 1024) + Color.RESET)
    last_disk_read = msg['data'][5]
    if last_disk_write > 0:
        disk_write = (msg['data'][6] - last_disk_write) / (msg['timestamp'] - last_time)
        sys.stdout.write(Color.PURPLE + "Disk-Write: {:.2f} MB/s".format(disk_write * 1024) + Color.RESET)
    last_disk_write = msg['data'][6]
    sys.stdout.flush()
    last_time = msg['timestamp']


if __name__ == '__main__':
    sub = Subscriber('/a2rl/monit', 'std_msgs::NumberMultiArray', callback_f,
                     ip='47.91.115.171')  # 47.91.115.171
    sub.wait_key()
