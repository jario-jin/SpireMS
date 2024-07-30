#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import cv2

from spirems import Publisher, Subscriber, get_all_msg_types, cvimg2sms, sms2cvimg
import threading
import time


pub = Publisher('/testcase/num_arr_v3', 'std_msgs::Null')
cnt = 2000000
while True:
    time.sleep(0.01)
    tpc = get_all_msg_types()['std_msgs::Null'].copy()
    tpc['data'] = [cnt]
    cnt += 1
    pub.publish(tpc, enforce=True)
