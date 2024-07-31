#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import time

from spirems import Subscriber
import time


def callback_f(msg):
    print(msg['data'])


sub = Subscriber(
    '/talker/hello_spirems',
    'std_msgs::String', callback_f
)
sub.wait_key()
