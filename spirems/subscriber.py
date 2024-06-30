#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import socket
import threading
import time

from spirems.log import get_logger
from spirems.msg_helper import (get_all_msg_types, encode_msg, check_topic_url, decode_msg, check_msg,
                                index_msg_header, decode_msg_header)


logger = get_logger('Subscriber')


class Subscriber(threading.Thread):

    def __init__(self, topic_url: str, topic_type: str, callback_func: callable,
                 ip: str = '127.0.0.1', port: int = 9094):
        threading.Thread.__init__(self)
        self.topic_url = topic_url
        self.topic_type = topic_type
        self.ip = ip
        self.port = port
        self.topic_type = topic_type
        self.topic_url = topic_url
        self.callback_func = callback_func

        all_types = get_all_msg_types()
        if topic_type not in all_types.keys():
            raise ValueError('The topic type is not present, please check...')
        url_state = check_topic_url(topic_url)
        if url_state != 0:
            raise ValueError('The input topic_url is invalid, please verify...')

        self.last_send_time = 0.0
        self.force_quit = False
        self.heartbeat_thread = None
        self.heartbeat_running = False
        self.running = True
        try:
            self._link()
        except Exception as e:
            pass
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

    def heartbeat(self):
        while self.heartbeat_running:
            all_types = get_all_msg_types()
            try:
                if time.time() - self.last_send_time >= 1.0:
                    apply_topic = all_types['_sys_msgs::Subscriber'].copy()
                    apply_topic['topic_type'] = self.topic_type
                    apply_topic['url'] = self.topic_url
                    self.client_socket.sendall(encode_msg(apply_topic))
                    self.last_send_time = time.time()
            except Exception as e:
                logger.error("heartbeat: {}".format(e))
            time.sleep(1)
            if self.force_quit:
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

    def suspend(self):
        if self.running and self.heartbeat_running:
            try:
                suspend_msg = get_all_msg_types()['_sys_msgs::Suspend'].copy()
                self.client_socket.sendall(encode_msg(suspend_msg))
                self.last_send_time = time.time()
            except Exception as e:
                pass

    def unsuspend(self):
        if self.running and self.heartbeat_running:
            try:
                suspend_msg = get_all_msg_types()['_sys_msgs::Unsuspend'].copy()
                self.client_socket.sendall(encode_msg(suspend_msg))
                self.last_send_time = time.time()
            except Exception as e:
                pass

    def _parse_msg(self, msg):
        response = get_all_msg_types()['_sys_msgs::Result'].copy()
        success, decode_data = decode_msg(msg)
        if success and decode_data['type'] == '_sys_msgs::TopicDown':
            # print("{:.3f}: {}".format(time.time() - decode_data['timestamp'], decode_data))
            self.callback_func(decode_data['topic'])
            response['id'] = decode_data['id']
            self.client_socket.sendall(encode_msg(response))
            self.last_send_time = time.time()
        elif not success:
            logger.debug(msg)

    def run(self):
        data = b''
        last_data = b''
        big_msg = 0
        while self.running:
            if self.force_quit:
                break
            try:
                data = self.client_socket.recv(1024 * 1024)  # 64K, 65536
                if not data:
                    raise TimeoutError('No data arrived.')
                # print('data: {}'.format(data))
            except TimeoutError as e:
                logger.error("subscriber recv: {}".format(e))
                # print(time.time() - tt1)
                self.running = False
                data = b''
            except Exception as e:
                logger.error("subscriber recv: {}".format(e))
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
                logger.error(e)
                self.running = False

            while not self.running:
                if self.force_quit:
                    break
                logger.info('(1) running=False, heartbeat_running=False')
                self.heartbeat_running = False
                try:
                    self.client_socket.close()
                    logger.info('(2) client_socket closed')
                except Exception as e:
                    logger.error(e)
                time.sleep(5)
                logger.info('(3) start re-linking ...')
                try:
                    self._link()
                    self.running = True
                    logger.info('(4) running=True, suspended=False')
                except Exception as e:
                    logger.error(e)
                logger.info('Running={}, Wait ...'.format(self.running))
                data = b''
                last_data = b''
                big_msg = 0


max_dt = 0


def callback_f(msg):
    global max_dt
    print("Dt: {}".format(time.time() - msg['timestamp']))
    if time.time() - msg['timestamp'] > max_dt:
        max_dt = time.time() - msg['timestamp']
        print("Max-Dt: {}".format(max_dt))


if __name__ == '__main__':
    sub = Subscriber('/sensors/hello/a12', 'std_msgs::NumberMultiArray', callback_f,
                     ip='127.0.0.1')
    # sub.wait_key()

    sus = False
    while True:
        if not sus:
            print("sub.suspend()")
            sub.suspend()
            sus = True
        else:
            print("sub.unsuspend()")
            sub.unsuspend()
            sus = False
        time.sleep(10)
