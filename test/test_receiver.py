#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import cv2

from spirems import Subscriber
import threading
import time


def callback_f(msg):
    # print(msg)
    print(msg['str2'])


sub = Subscriber('/test/msg123', 'std_msgs::Null', callback_f)
