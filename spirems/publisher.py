#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import logging
import random
import socket
import threading
import time
from jsonschema import validate
from spirems.log import get_logger
from spirems.msg_helper import (get_all_msg_types, get_all_msg_schemas, def_msg, encode_msg, check_topic_url,
                                decode_msg, check_msg,
                                index_msg_header, decode_msg_header)


logger = get_logger('Publisher')


class Publisher(threading.Thread):

    def __init__(self, topic_url: str, topic_type: str, ip: str = '127.0.0.1', port: int = 9094):
        threading.Thread.__init__(self)
        self.topic_url = topic_url
        self.topic_type = topic_type
        self.ip = ip
        self.port = port
        self.topic_type = topic_type
        self.topic_url = topic_url

        all_types = get_all_msg_types()
        if topic_type not in all_types.keys():
            raise ValueError('The topic type is not present, please check...')
        url_state = check_topic_url(topic_url)
        if url_state != 0:
            raise ValueError('The input topic_url is invalid, please verify...')

        self.upload_id = 0
        self.last_send_time = 0.0
        self.last_upload_time = 0.0
        self.uploaded_ids = dict()  # already uploaded IDs
        self._ids_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self.transmission_delay = 0.0  # second
        self.package_loss_rate = 0.0  # 0-100 %
        self.force_quit = False
        self.heartbeat_thread = None
        self.heartbeat_running = False
        self.running = True
        self.enforce_publish = False
        try:
            self._link()
        except Exception as e:
            logger.warning("({}) __init__: {}".format(self.topic_url, e))
        self.suspended = False
        self.err_cnt = 0
        self.start()

    def kill(self):
        self.force_quit = True

    def wait_key(self):
        try:
            while not self.force_quit:
                time.sleep(0.5)
        except KeyboardInterrupt:
            logger.info('stopped by keyboard')
            self.kill()
            self.join()

    def _delay_packet_loss_rate(self):
        delay = 0.0
        delay_cnt = 0
        package_loss_rate = 0.0
        package_len = len(self.uploaded_ids)
        invalid_keys = []

        with self._ids_lock:
            for key, val in self.uploaded_ids.items():
                if val[1] >= 0:
                    delay += val[1]
                    delay_cnt += 1
                if time.time() - val[0] > 5:  # keep 5 second for each msg
                    invalid_keys.append(key)
                    package_loss_rate += 1

        with self._ids_lock:
            for key in invalid_keys:
                del self.uploaded_ids[key]

        if delay_cnt > 0:
            delay = delay / delay_cnt
        self.transmission_delay = delay
        if package_len > 0:
            package_loss_rate = package_loss_rate / package_len
        self.package_loss_rate = package_loss_rate

    def heartbeat(self):
        while self.heartbeat_running:
            try:
                apply_topic = def_msg('_sys_msgs::Publisher')
                apply_topic['topic_type'] = self.topic_type
                apply_topic['url'] = self.topic_url
                apply_topic['enforce'] = self.enforce_publish
                if time.time() - self.last_send_time >= 1.0:
                    with self._send_lock:
                        self.client_socket.sendall(encode_msg(apply_topic))
                    self.last_send_time = time.time()

                self._delay_packet_loss_rate()
            except Exception as e:
                logger.warning("({}) heartbeat: {}".format(self.topic_url, e))

            time.sleep(1)
            if self.force_quit:
                self.heartbeat_running = False
                break

    def _link(self):
        self.heartbeat_running = False
        if self.heartbeat_thread is not None:
            self.heartbeat_thread.join()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.settimeout(5)
        self.client_socket.connect((self.ip, self.port))
        self.heartbeat_thread = threading.Thread(target=self.heartbeat)
        self.heartbeat_running = True
        self.heartbeat_thread.start()

    def idle_time(self):
        return time.time() - self.last_upload_time

    def publish(self, topic: dict, enforce: bool = False) -> bool:
        if topic['type'] in get_all_msg_schemas():
            validate(instance=topic, schema=get_all_msg_schemas()[topic['type']])
        if not self.suspended and self.running:
            self.enforce_publish = enforce
            if time.time() - self.last_upload_time > self.transmission_delay * 0.3 or enforce:
                try:
                    # logger.info("avg_delay: {}".format(self.transmission_delay))
                    topic = topic.copy()
                    if 'timestamp' in topic.keys() and topic['timestamp'] == 0.0:
                        topic['timestamp'] = time.time()
                    topic_upload = def_msg('_sys_msgs::TopicUpload')
                    topic_upload['topic'] = topic
                    self.upload_id += 1
                    if self.upload_id > 1e6:
                        self.upload_id = 1
                    topic_upload['id'] = self.upload_id
                    with self._ids_lock:
                        self.uploaded_ids[self.upload_id] = [time.time(), -1]  # Now, Delay
                    with self._send_lock:
                        self.client_socket.sendall(encode_msg(topic_upload))
                    self.last_send_time = time.time()
                    self.last_upload_time = time.time()
                    return True
                except Exception as e:
                    logger.warning("({}) publish: {}".format(self.topic_url, e))
            else:
                pass
                # logger.warn("There is a large network delay ({}), suspend sending once.".format(self.transmission_delay))
        return False

    def _parse_msg(self, msg):
        success, decode_data = decode_msg(msg)
        if success and decode_data['type'] == '_sys_msgs::Suspend':
            self.suspended = True
        elif success and decode_data['type'] == '_sys_msgs::Unsuspend':
            self.suspended = False
        elif success and decode_data['type'] == '_sys_msgs::Result':
            if decode_data['id'] > 0:
                self.err_cnt = 0
                recv_id = decode_data['id']
                # print(decode_data['id'])
                with self._ids_lock:
                    if recv_id in self.uploaded_ids:
                        self.uploaded_ids[recv_id][1] = time.time() - self.uploaded_ids[recv_id][0]
            if decode_data['error_code'] > 0:
                self.err_cnt += 1
                if self.err_cnt > 5:
                    self.suspended = True
            # logger.debug("{}, {}".format(self.suspended, decode_data))
        elif success and decode_data['type'] != '_sys_msgs::HeartBeat':
            logger.debug(decode_data)

    def run(self):
        data = b''
        last_data = b''
        big_msg = 0
        while self.running:
            if self.force_quit:
                self.running = False
                break
            try:
                data = self.client_socket.recv(65536)  # 4096
                if not data:
                    raise TimeoutError('No data arrived.')
                # print('data: {}'.format(data))
            except TimeoutError as e:
                logger.warning("({}) recv(1): {}".format(self.topic_url, e))
                # print(time.time() - tt1)
                self.running = False
                data = b''
            except Exception as e:
                logger.warning("({}) recv(2): {}".format(self.topic_url, e))
                self.running = False
                data = b''

            try:
                recv_msgs = []
                checked_msgs, parted_msgs, parted_lens = check_msg(data)

                if len(parted_msgs) > 0:
                    for parted_msg, parted_len in zip(parted_msgs, parted_lens):
                        if parted_len > 0:
                            last_data = parted_msg
                            big_msg = parted_len
                        else:
                            last_data += parted_msg
                            if 0 < big_msg <= len(last_data):
                                recv_msgs.append(last_data[:big_msg])
                                big_msg = 0
                                last_data = b''

                recv_msgs.extend(checked_msgs)
                if len(recv_msgs) > 0:
                    for msg in recv_msgs:
                        self._parse_msg(msg)

            except Exception as e:
                logger.warning("({}) parse: {}".format(self.topic_url, e))
                self.running = False

            while not self.running:
                if self.force_quit:
                    break
                # logger.info('(1) running=False, suspended=True, heartbeat_running=False')
                self.suspended = True
                self.heartbeat_running = False
                try:
                    self.client_socket.close()
                    # logger.info('(2) client_socket closed')
                except Exception as e:
                    logger.warning("({}) socket_close: {}".format(self.topic_url, e))
                time.sleep(5)
                # logger.info('(3) start re-linking ...')
                try:
                    self._link()
                    self.running = True
                    self.suspended = False
                    # logger.info('(4) running=True, suspended=False')
                except Exception as e:
                    logger.warning("({}) relink: {}".format(self.topic_url, e))
                logger.info('Running={}, Wait ...'.format(self.running))
                data = b''
                last_data = b''
                big_msg = 0


if __name__ == '__main__':
    pub1 = Publisher('/sensors/hello/a12', 'std_msgs::NumberMultiArray',
                    ip='127.0.0.1')
    time.sleep(0.1)
    pub2 = Publisher('/sensors/hello/a12', 'std_msgs::NumberMultiArray',
                    ip='127.0.0.1')
    # pub = Publisher('/hello1', 'std_msgs::NumberMultiArray')
    cnt = 0
    while True:
        time.sleep(0.1)
        tpc = def_msg('std_msgs::NumberMultiArray')
        data = [123]
        # data.extend(random.random() for i in range(20))
        tpc['data'] = data
        # print(len(encode_msg(tpc)) / 1024 / 1024)
        # if cnt == 0:
        #     tpc['type'] = 'std_msgs::Number'
        pub1.publish(tpc, True)
        tpc = def_msg('std_msgs::NumberMultiArray')
        tpc['data'] = [456]
        pub2.publish(tpc, True)
        cnt += 1
