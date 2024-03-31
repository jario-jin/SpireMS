#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from spirems.subscriber import Subscriber
from spirems.image_io.adaptor import sms2cvimg
import time
import cv2


def callback_f(msg):
    # print(time.time() - msg['timestamp'])
    img2 = sms2cvimg(msg)
    cv2.imshow('img', img2)
    cv2.waitKey(5)


if __name__ == '__main__':
    sub = Subscriber('/sensors/camera/image_raw', 'sensor_msgs::Image', callback_f,
                     ip='127.0.0.1')  # 47.91.115.171
    sub.wait_key()
