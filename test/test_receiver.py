#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import cv2

from spirems import Publisher, Subscriber, get_all_msg_types, cvimg2sms, sms2cvimg
import threading
import time


def callback_f(msg):
    print(msg['data'])


sub = Subscriber('/testcase/num_arr_v3', 'std_msgs::Null', callback_f)
