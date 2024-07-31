#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from spirems.subscriber import Subscriber
from spirems.publisher import Publisher
from spirems.image_io.adaptor import sms2cvimg, cvimg2sms
from spirems.image_io.visual_helper import load_a2rl_logo
import time
import cv2


def callback_f(msg):
    # print(time.time() - msg['timestamp'])
    # print(type(msg))
    dt1 = time.time() - msg['timestamp']
    img2 = sms2cvimg(msg)
    dt2 = time.time() - msg['timestamp']
    print("DT1: {}, DT2: {}".format(dt1, dt2))
    img2 = cv2.resize(img2, (1280, 720))
    cv2.imshow("img2", img2)
    cv2.waitKey(5)


if __name__ == '__main__':
    sub = Subscriber('/sensors/camera/image_raw', 'sensor_msgs::CompressedImage', callback_f)
    pub = Publisher('/sensors/camera/image_raw', 'sensor_msgs::CompressedImage')
    while True:
        img = load_a2rl_logo()
        img = cv2.resize(img, (1920, 1200))
        sms = cvimg2sms(img, format='jpg')
        pub.publish(sms)
        time.sleep(0.1)

    sub.wait_key()
