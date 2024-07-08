#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import cv2

from spirems import Publisher, Subscriber, get_all_msg_types, cvimg2sms, sms2cvimg
import threading
import time
import concurrent.futures
from spirems.log import get_logger
logger = get_logger('TestCaseMsgIntervalOne')


max_dt = 0
t1 = 0
n_timer_msgs = 0
t_timer = 0
fps_timer = 0


def callback_f(msg):
    global max_dt, t1
    global n_timer_msgs, t_timer, fps_timer
    if t_timer == 0:
        t_timer = time.time()
    if time.time() - t_timer >= 1.0:
        fps_timer = n_timer_msgs / (time.time() - t_timer)
        n_timer_msgs = 0
        t_timer = time.time()
    n_timer_msgs += 1
    # print("Msg: {}".format(msg))
    if t1 != 0 and time.time() - t1 > max_dt:
        max_dt = time.time() - t1
        logger.warning("TimerOne Max-Dt: {}".format(max_dt))
    t1 = time.time()


sub = Subscriber('/testcase/num_arr_v2', 'std_msgs::Null', callback_f)
pub = Publisher('/testcase/num_arr_v2', 'std_msgs::Null')
cnt = 0
while True:
    time.sleep(0.01)
    tpc = get_all_msg_types()['std_msgs::Null'].copy()
    tpc['data'] = [cnt]
    cnt += 1
    pub.publish(tpc, enforce=True)