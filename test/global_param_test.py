#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-08-04

import cv2

from spirems import Parameter, Publisher, Subscriber, get_all_msg_types, cvimg2sms, sms2cvimg
import threading
import time


def params_changed(msg):
    print(params_changed, msg)


param2 = Parameter('MyNode', params_changed)
param2.set_param('hello', '222')
param2.set_param('world', [1, 2, 3, 45])


param1 = Parameter('_global', params_changed)
param1.set_param('/_global/dataset', 'coco')

params = param1.get_all_params()
print(params)




