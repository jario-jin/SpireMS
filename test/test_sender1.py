#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import cv2

from spirems import Publisher, Subscriber, def_msg
import threading
import time


pub = Publisher('/test/msg123', 'std_msgs::Null')
cnt = 1
while True:
    time.sleep(0.1)
    tpc = def_msg('std_msgs::Null')
    tpc['cnt'] = cnt
    cnt += 1
    tpc['str1'] = "hello!!"
    tpc['str2'] = "hello2!@@@"
    pub.publish(tpc)
