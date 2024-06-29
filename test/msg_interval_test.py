#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import cv2

from spirems import Publisher, Subscriber, get_all_msg_types, cvimg2sms, sms2cvimg
import threading
import time
import concurrent.futures


max_dt = 0
t1 = 0


def callback_f(msg):
    global max_dt, t1
    # print("Dt: {}".format(time.time() - msg['timestamp']))
    if t1 != 0 and time.time() - t1 > max_dt:
        max_dt = time.time() - t1
        print("Max-Dt: {}".format(max_dt))
    t1 = time.time()


def callback_g(msg):
    cvimg = sms2cvimg(msg)
    cv2.imshow("cvimg", cvimg)
    cv2.waitKey(5)


def timer_callback():
    pub = Publisher('/testcase/num_arr', 'std_msgs::NumberMultiArray')
    cnt = 0
    while True:
        time.sleep(0.02)
        tpc = get_all_msg_types()['std_msgs::NumberMultiArray'].copy()
        tpc['data'] = [cnt]
        cnt += 1
        pub.publish(tpc)


def img_callback():
    pub = Publisher('/testcase/image', 'sensor_msgs::Image')
    cap = cv2.VideoCapture(0)
    while True:
        time.sleep(0.05)
        _, frame = cap.read()
        tpc = cvimg2sms(frame)
        pub.publish(tpc)


sub1 = Subscriber('/testcase/num_arr', 'std_msgs::NumberMultiArray', callback_f)
sub2 = Subscriber('/testcase/image', 'sensor_msgs::Image', callback_g)


with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.submit(timer_callback)
    executor.submit(img_callback)



