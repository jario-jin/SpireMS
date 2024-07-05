#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import threading
import time
import uuid
from queue import Queue

import cv2
from spirems import Subscriber, Publisher, get_all_msg_types, cvimg2sms


external_input_url = "/SpireView/CVJobInput"
internal_input_url = "/SpireView/CVJobResultsInput"
supported_algorithms = ["YOLOv8"]
external_ip, external_port = "127.0.0.1", 9094
internal_ip, internal_port = "127.0.0.1", 9094


class SpireViewPipeline(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.e_job_sub = Subscriber(
            external_input_url, "wedet_msgs::CVJob", self.parse_cv_job, ip=external_ip, port=external_port)
        self.job_queue = Queue()
        self._j_queue_lock = threading.Lock()
        self.res_queue = Queue()
        self._r_queue_lock = threading.Lock()
        self.i_res_sub = Subscriber(
            internal_input_url, "std_msgs::Null", self.parse_results, ip=internal_ip, port=internal_port)
        self.i_job_pubs = dict()
        for alg in supported_algorithms:
            pub_url = "/SpireView/{}/CVJobInput".format(alg.replace('-', '_'))
            self.i_job_pubs[alg] = Publisher(
                pub_url, "wedet_msgs::CVJob", ip=internal_ip, port=internal_port)
        self.e_job_pubs = dict()
        self.running = True

    def parse_results(self, msg):
        self._r_queue_lock.acquire()
        self.res_queue.put(msg)
        self._r_queue_lock.release()

    def parse_cv_job(self, msg):
        self._j_queue_lock.acquire()
        self.job_queue.put(msg)
        self._j_queue_lock.release()

    def run(self):
        while self.running:
            while not self.job_queue.empty() or not self.res_queue.empty():
                if not self.job_queue.empty():
                    self._j_queue_lock.acquire()
                    msg = self.job_queue.get()
                    self._j_queue_lock.release()
                    if msg['algorithm'] in supported_algorithms:
                        self.i_job_pubs[msg['algorithm']].publish(msg, enforce=True)

                if not self.res_queue.empty():
                    self._r_queue_lock.acquire()
                    msg = self.res_queue.get()
                    self._r_queue_lock.release()
                    res_url = "/SpireView/{}/CVJobResults".format(msg['client_id'])
                    if msg['client_id'] not in self.e_job_pubs:
                        e_pub = Publisher(res_url, msg['type'], ip=external_ip, port=external_port)
                        self.e_job_pubs[msg['client_id']] = e_pub
                    self.e_job_pubs[msg['client_id']].publish(msg, enforce=True)

            to_remove = []
            for key, pub in self.e_job_pubs.items():
                if pub.idle_time() > 600:
                    pub.kill()
                    to_remove.append(key)
            for key in to_remove:
                del self.e_job_pubs[key]

            time.sleep(0.01)


if __name__ == '__main__':
    pipeline = SpireViewPipeline()
    pipeline.start()
    pub1 = Publisher(external_input_url, 'wedet_msgs::CVJob')
    img = cv2.imread(r'C:\Users\jario\Pictures\20240405034546.jpg')
    while True:
        time.sleep(0.1)
        tpc = get_all_msg_types()['wedet_msgs::CVJob'].copy()
        tpc['algorithm'] = 'YOLOv8'
        tpc['image'] = cvimg2sms(img)
        pub1.publish(tpc)
