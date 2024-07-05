#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import threading
import time
import uuid
from queue import Queue

import cv2

from spirems import Subscriber, Publisher, get_all_msg_types, sms2cvimg


algorithm = "YOLOv8"
input_url = "/SpireView/{}/CVJobInput".format(algorithm)
output_url = "/SpireView/CVJobResultsInput"
internal_ip, internal_port = "127.0.0.1", 9094


class SpireViewYOLOv8(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.cv_job_sub = Subscriber(
            input_url, "wedet_msgs::CVJob", self.parse_cv_job, ip=internal_ip, port=internal_port)
        self.res_pub = Publisher(
            output_url, "wedet_msgs::DetResult", ip=internal_ip, port=internal_port)
        self.job_queue = Queue()
        self._queue_lock = threading.Lock()
        self.running = True

    def parse_cv_job(self, msg):
        self._queue_lock.acquire()
        self.job_queue.put(msg)
        self._queue_lock.release()

    def run(self):
        while self.running:
            while not self.job_queue.empty():
                self._queue_lock.acquire()
                msg = self.job_queue.get()
                self._queue_lock.release()
                img = sms2cvimg(msg['image'])
                print(img.shape)

                res = get_all_msg_types()['wedet_msgs::DetResult'].copy()
                res['client_id'] = msg['client_id']
                self.res_pub.publish(res)
            time.sleep(0.01)


if __name__ == '__main__':
    yolo = SpireViewYOLOv8()
    yolo.start()
