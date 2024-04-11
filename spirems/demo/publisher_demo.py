#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from spirems import Publisher, get_all_msg_types
import time
import random


pub = Publisher(
    '/talker/hello_spirems',
    'std_msgs::NumberMultiArray',
    # ip='47.91.115.171'
)

while True:
    time.sleep(0.01)
    tpc = get_all_msg_types()['std_msgs::NumberMultiArray'].copy()
    tpc['data'] = [random.random() for i in range(4)]
    pub.publish(tpc)
