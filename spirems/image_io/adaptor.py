#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import cv2
import numpy as np
import base64
from spirems.msg_helper import get_all_msg_types
from spirems.publisher import Publisher


def cvimg2sms(img: np.ndarray) -> dict:
    sms = get_all_msg_types()['sensor_msgs::Image'].copy()
    sms['height'] = img.shape[0]
    sms['width'] = img.shape[1]
    sms['encoding'] = 'uint8'

    success, img_jpg = cv2.imencode('.jpg', img)
    if success:
        img_base64 = base64.b64encode(img_jpg).decode('utf-8')
        sms['data'] = img_base64

    return sms


def sms2cvimg(sms: dict) -> np.ndarray:
    img_base64 = base64.b64decode(sms['data'])
    img_jpg = np.frombuffer(img_base64, dtype='uint8')
    img = cv2.imdecode(img_jpg, cv2.IMREAD_COLOR)
    return img


if __name__ == '__main__':
    cap = cv2.VideoCapture(0)
    pub = Publisher('/sensors/camera/image_raw', 'sensor_msgs::Image',
                    ip='47.91.115.171')  # 47.91.115.171
    while True:
        try:
            ret, img1 = cap.read()
            img1 = cv2.resize(img1, (640, 360))
            sms = cvimg2sms(img1)
            pub.publish(sms)
            # img2 = sms2cvimg(sms)
            # cv2.imshow('img', img2)
            cv2.waitKey(50)
        except KeyboardInterrupt:
            print('stopped by keyboard')
            pub.kill()
            pub.join()
