#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import cv2

from spirems import Publisher, Subscriber, get_all_msg_types, cvimg2sms, sms2cvimg
import threading
import time
import concurrent.futures
from spirems.log import get_logger
logger = get_logger('TestCaseMsgIntervalMulti')

vid_dir = "F:/002.mkv"
max_dt = 0
t1 = 0
max_dt_img = 0
t2 = 0
max_dt_cam = 0
t3 = 0
n_timer_msgs = 0
t_timer = 0
fps_timer = 0
n_img_msgs = 0
t_img = 0
fps_img = 0
n_cam_msgs = 0
t_cam = 0
fps_cam = 0


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
    # print("Dt: {}".format(time.time() - msg['timestamp']))
    if t1 != 0 and time.time() - t1 > max_dt:
        max_dt = time.time() - t1
        logger.warning("Timer Max-Dt: {}, Image: {}, Camera: {}".format(max_dt, max_dt_img, max_dt_cam))
    t1 = time.time()


def callback_g(msg):
    global max_dt_img, t2
    global n_img_msgs, t_img, fps_img
    if t_img == 0:
        t_img = time.time()
    if time.time() - t_img >= 1.0:
        fps_img = n_img_msgs / (time.time() - t_img)
        n_img_msgs = 0
        t_img = time.time()
        print("Img-Fps: {}, Cam-Fps: {} Timer-Fps: {}, Max-Dt: {}, {}, {}".format(fps_img, fps_cam, fps_timer, max_dt_img, max_dt_cam, max_dt))
    n_img_msgs += 1

    if t2 != 0 and time.time() - t2 > max_dt_img:
        max_dt_img = time.time() - t2
        logger.warning("Image Max-Dt: {}, Timer: {}, Camera: {}".format(max_dt_img, max_dt, max_dt_cam))
    t2 = time.time()

    cvimg = sms2cvimg(msg)
    cv2.imshow("cvimg", cvimg)
    cv2.waitKey(5)


def callback_h(msg):
    global max_dt_cam, t3
    global n_cam_msgs, t_cam, fps_cam
    if t_cam == 0:
        t_cam = time.time()
    if time.time() - t_cam >= 1.0:
        fps_cam = n_cam_msgs / (time.time() - t_cam)
        n_cam_msgs = 0
        t_cam = time.time()
    n_cam_msgs += 1

    if t3 != 0 and time.time() - t3 > max_dt_cam:
        max_dt_cam = time.time() - t3
        logger.warning("Camera Max-Dt: {}, Timer: {}, Image: {}".format(max_dt_cam, max_dt, max_dt_img))
    t3 = time.time()

    cvimg = sms2cvimg(msg)
    cv2.imshow("camera", cvimg)
    cv2.waitKey(5)


def timer_callback():
    pub = Publisher('/testcase/num_arr', 'std_msgs::NumberMultiArray')
    cnt = 0
    while True:
        time.sleep(0.01)
        tpc = get_all_msg_types()['std_msgs::NumberMultiArray'].copy()
        tpc['data'] = [cnt]
        cnt += 1
        pub.publish(tpc, enforce=True)


def img_callback():
    pub = Publisher('/testcase/image', 'sensor_msgs::CompressedImage')
    cap = cv2.VideoCapture(vid_dir)
    while True:
        time.sleep(0.02)
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (0, 0), None, 0.5, 0.5)
            tpc = cvimg2sms(frame)
            pub.publish(tpc)
        else:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)


def cam_callback():
    pub = Publisher('/testcase/camera', 'sensor_msgs::CompressedImage')
    cap = cv2.VideoCapture(0)
    while True:
        time.sleep(0.02)
        ret, frame = cap.read()
        if ret:
            # frame = cv2.resize(frame, (0, 0), None, 0.5, 0.5)
            tpc = cvimg2sms(frame)
            pub.publish(tpc)


sub1 = Subscriber('/testcase/num_arr', 'std_msgs::NumberMultiArray', callback_f)
sub2 = Subscriber('/testcase/image', 'sensor_msgs::CompressedImage', callback_g)
sub3 = Subscriber('/testcase/camera', 'sensor_msgs::CompressedImage', callback_h)


with concurrent.futures.ThreadPoolExecutor() as executor:
    executor.submit(timer_callback)
    executor.submit(img_callback)
    # executor.submit(cam_callback)

