#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import time

try:
    import cv2
except Exception as e:
    pass
import numpy as np
import base64
from spirems.msg_helper import get_all_msg_types, def_msg
from spirems.publisher import Publisher


def cvimg2sms(img: np.ndarray, format='jpeg', frame_id='camera') -> dict:
    assert len(img.shape) == 3 and img.shape[0] > 0 and img.shape[1] > 0 and img.shape[2] == 3 \
           and img.dtype == np.uint8, "CHECK img.ndim == 3 and img.dtype == np.uint8!"
    sms = def_msg('sensor_msgs::CompressedImage')
    sms['timestamp'] = time.time()
    sms['frame_id'] = frame_id
    sms['format'] = format

    # t1 = time.time()
    if sms['format'] in ['jpeg', 'jpg']:
        success, img_encoded = cv2.imencode('.jpg', img)
    elif sms['format'] == 'png':
        success, img_encoded = cv2.imencode('.png', img)
    elif sms['format'] == 'webp':
        success, img_encoded = cv2.imencode('.webp', img, [cv2.IMWRITE_WEBP_QUALITY, 50])
    # print("-- imencode: {}".format(time.time() - t1))
    """
    elif sms['format'] == 'uint8':
        img_encoded = img.tobytes()
    """

    # t1 = time.time()
    img_base64 = base64.b64encode(img_encoded).decode('utf-8')
    # print("-- b64encode: {}".format(time.time() - t1))
    sms['data'] = img_base64

    return sms


def sms2cvimg(sms: dict) -> np.ndarray:
    # t1 = time.time()
    img_base64 = base64.b64decode(sms['data'])
    # print("== b64decode: {}".format(time.time() - t1))

    assert sms['format'] in ['jpeg', 'jpg', 'png', 'webp']
    img_encoded = np.frombuffer(img_base64, dtype='uint8')
    img = cv2.imdecode(img_encoded, cv2.IMREAD_COLOR)
    """
    elif sms['format'] == 'uint8':
        img = np.frombuffer(img_base64, dtype='uint8')
        img = img.reshape(sms['height'], sms['width'], sms['channel'])
    """

    return img


if __name__ == '__main__':
    cap = cv2.VideoCapture(r'F:\005.mp4')
    # img1 = cv2.imread(r'C:\Users\jario\Pictures\2023-04-09-114628.png')
    pub = Publisher('/sensors/camera/image_raw', 'sensor_msgs::CompressedImage')
    while True:
        try:
            ret, img1 = cap.read()
            img1 = cv2.resize(img1, (1280, 640))
            sms = cvimg2sms(img1, format='jpeg')
            pub.publish(sms)
            cv2.waitKey(30)
        except KeyboardInterrupt:
            print('stopped by keyboard')
            pub.kill()
            pub.join()
