#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import time

from spirems import Subscriber
import time


def callback_f(msg):
    print(time.time() - msg['timestamp'])


sub = Subscriber(
    '/talker/hello_spirems',
    'std_msgs::NumberMultiArray', callback_f,
    # ip='47.91.115.171'
)
sub.wait_key()
