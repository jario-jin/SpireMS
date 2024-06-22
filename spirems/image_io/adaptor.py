#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import time

try:
    import cv2
except Exception as e:
    pass
import numpy as np
import base64
from spirems.msg_helper import get_all_msg_types
from spirems.publisher import Publisher


def cvimg2sms(img: np.ndarray, encoding='jpeg') -> dict:
    sms = get_all_msg_types()['sensor_msgs::Image'].copy()
    sms['timestamp'] = time.time()
    sms['height'] = img.shape[0]
    sms['width'] = img.shape[1]
    sms['channel'] = img.shape[2]
    sms['encoding'] = encoding

    if sms['encoding'] in ['jpeg', 'jpg']:
        success, img_encoded = cv2.imencode('.jpg', img)
    elif sms['encoding'] == 'png':
        success, img_encoded = cv2.imencode('.png', img)
    elif sms['encoding'] == 'uint8':
        img_encoded = img.tobytes()

    # t1 = time.time()
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    # print("-- b64encode: {}".format(time.time() - t1))
    sms['data'] = img_base64

    return sms


def sms2cvimg(sms: dict) -> np.ndarray:
    # t1 = time.time()
    img_base64 = base64.b64decode(sms['data'])
    # print("== b64decode: {}".format(time.time() - t1))

    if sms['encoding'] in ['jpeg', 'jpg', 'png']:
        img_encoded = np.frombuffer(img_base64, dtype='uint8')
        img = cv2.imdecode(img_encoded, cv2.IMREAD_COLOR)
    elif sms['encoding'] == 'uint8':
        img = np.frombuffer(img_base64, dtype='uint8')
        img = img.reshape(sms['height'], sms['width'], sms['channel'])

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
