#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import threading
import time
import uuid
from queue import Queue

import cv2
from spirems import Subscriber, Publisher, get_all_msg_types, cvimg2sms


external_input_url = "/SpireView/TaskInput"
internal_input_url = "/SpireView/TaskResultsInput"
supported_jobs = {
    "SpireDet": {"input": "sensor_msgs::CompressedImage", "output": "spirecv_msgs::2DTargets"},
    "YOLOv8": {"input": "sensor_msgs::CompressedImage", "output": "spirecv_msgs::2DTargets"},
    "Detection2DEval": {"input": "spirecv_msgs::2DTargets", "output": "spirecv_msgs::EvaluationResult"}
}
external_ip, external_port = "127.0.0.1", 9094
internal_ip, internal_port = "127.0.0.1", 9094


class SpireViewPipeline(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.e_job_sub = Subscriber(
            external_input_url, "spirecv_msgs::Task", self.parse_cv_job, ip=external_ip, port=external_port)
        self.job_queue = Queue()
        self.res_queue = Queue()
        self.i_res_sub = Subscriber(
            internal_input_url, "std_msgs::Null", self.parse_results, ip=internal_ip, port=internal_port)
        self.i_job_pubs = dict()
        for alg in supported_jobs.keys():
            pub_url = "/SpireView/{}/TaskInput".format(alg.replace('-', '_'))
            self.i_job_pubs[alg] = Publisher(
                pub_url, supported_jobs[alg]["input"], ip=internal_ip, port=internal_port)
        self.e_job_pubs = dict()

        self.running = True
        self.results_thread = threading.Thread(target=self.queue_results)
        self.results_thread.start()
        self.cv_job_thread = threading.Thread(target=self.queue_cv_job)
        self.cv_job_thread.start()
        self.start()

    def queue_results(self):
        while self.running:
            msg = self.res_queue.get(block=True)

            res_url = "/SpireView/{}/TaskResults".format(msg['client_id'])
            if res_url not in self.e_job_pubs:
                self.e_job_pubs[res_url] = Publisher(res_url, msg['type'], ip=external_ip, port=external_port)
            self.e_job_pubs[res_url].publish(msg, enforce=True)

    def queue_cv_job(self):
        while self.running:
            msg = self.job_queue.get(block=True)

            if 'client_id' in msg and 'job' in msg:
                img_msg = msg['data']
                img_msg['client_id'] = msg['client_id']
                if msg['job'] in supported_jobs:
                    self.i_job_pubs[msg['job']].publish(img_msg, enforce=True)

    def parse_results(self, msg):
        self.res_queue.put(msg)

    def parse_cv_job(self, msg):
        self.job_queue.put(msg)

    def run(self):
        while self.running:
            to_remove = []
            for key, pub in self.e_job_pubs.items():
                if pub.idle_time() > 600:
                    pub.kill()
                    pub.join()
                    to_remove.append(key)
            for key in to_remove:
                del self.e_job_pubs[key]

            time.sleep(1)


if __name__ == '__main__':
    pipeline = SpireViewPipeline()
    pipeline.join()
