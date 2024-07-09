#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import threading
import socket
import random
import time
import struct
from queue import Queue
from spirems.log import get_logger
from spirems.msg_helper import (get_all_msg_types, index_msg_header, decode_msg_header, decode_msg, encode_msg,
                                check_topic_url, check_msg)
from spirems.error_code import ec2msg


logger = get_logger('Server')
TOPIC_LIST = None
TOPIC_LIST_LOCK = threading.Lock()


def get_public_topic() -> dict:
    global TOPIC_LIST
    if TOPIC_LIST is None:
        TOPIC_LIST = {
            'from_topic': {},
            'from_key': {},
            'from_subscriber': {}
        }
    return TOPIC_LIST


def get_public_topic_list() -> list:
    topic_list = get_public_topic()
    urls = list(topic_list['from_topic'].keys())
    urls.sort()
    return urls


def show_topic_list():
    topic_list = get_public_topic()
    urls = list(topic_list['from_topic'].keys())
    urls.sort()
    for url in urls:
        logger.info("{} <{}> [{}]".format(
            topic_list['from_topic'][url]['url'],
            topic_list['from_topic'][url]['type'],
            topic_list['from_topic'][url]['key']
        ))


def sync_topic_subscriber():
    topic_list = get_public_topic()
    with TOPIC_LIST_LOCK:
        for topic in topic_list['from_topic'].keys():
            topic_list['from_topic'][topic]['subs'] = []
        for client_key, client in topic_list['from_subscriber'].items():
            if client['url'] in topic_list['from_topic']:
                if client['type'] == topic_list['from_topic'][client['url']]['type']:
                    topic_list['from_topic'][client['url']]['subs'].append(client_key)
                elif client['type'] == 'std_msgs::Null':
                    topic_list['from_topic'][client['url']]['subs'].append(client_key)


def remove_topic(client_key: str):
    topic_list = get_public_topic()
    if client_key in topic_list['from_key']:
        url = topic_list['from_key'][client_key]['url']
        with TOPIC_LIST_LOCK:
            del topic_list['from_topic'][url]
            del topic_list['from_key'][client_key]
        sync_topic_subscriber()


def remove_subscriber(client_key: str):
    topic_list = get_public_topic()
    if client_key in topic_list['from_subscriber']:
        with TOPIC_LIST_LOCK:
            del topic_list['from_subscriber'][client_key]
        sync_topic_subscriber()


def update_topic(topic_url: str, topic_type: str, client_key: str):
    topic_list = get_public_topic()
    if client_key not in topic_list['from_key']:
        with TOPIC_LIST_LOCK:
            topic_list['from_key'][client_key] = {
                'url': topic_url,
                'type': topic_type,
                'key': client_key
            }
            if topic_url in topic_list['from_topic']:
                topic_list['from_topic'][topic_url]['key'].append(client_key)
            else:
                topic_list['from_topic'][topic_url] = {
                    'url': topic_url,
                    'type': topic_type,
                    'key': [client_key]
                }
        sync_topic_subscriber()


def update_subscriber(topic_url: str, topic_type: str, client_key: str):
    topic_list = get_public_topic()
    if client_key not in topic_list['from_subscriber']:
        with TOPIC_LIST_LOCK:
            topic_list['from_subscriber'][client_key] = {
                'url': topic_url,
                'type': topic_type,
                'key': client_key
            }
        sync_topic_subscriber()


def check_publish_url_type(topic_url: str, topic_type: str, client_key: str) -> int:
    error = check_topic_url(topic_url)
    """
    if client_key not in get_public_topic()['from_key'] and topic_url in get_public_topic()['from_topic']:
        error = 204  # As the same as the existing
    """
    if topic_type not in get_all_msg_types():
        error = 205  # Unsupported topic type
    return error


def check_subscribe_url_type(topic_url: str, topic_type: str) -> int:
    error = check_topic_url(topic_url)
    if topic_type not in get_all_msg_types():
        error = 205  # Unsupported topic type
    return error


def random_vcode(k=6):
    vcode = ''.join(random.choices(
        ['z', 'y', 'x', 'w', 'v', 'u', 't', 's', 'r', 'q', 'p', 'o', 'n', 'm', 'l', 'k', 'j', 'i', 'h', 'g', 'f', 'e',
         'd', 'c', 'b', 'a', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'], k=k))
    return vcode


class Pipeline(threading.Thread):
    def __init__(self, client_key, client_socket, _server):
        threading.Thread.__init__(self)
        self.client_key = client_key
        self.client_socket = client_socket
        self._server = _server
        self.running = True
        self.pub_type = None
        self.pub_enforce = True
        self.sub_type = None
        self.sub_url = None
        self._quit = False
        self.pub_suspended = False
        self.sub_suspended = False
        self.pass_id = 0
        self.passed_ids = dict()  # already passed IDs
        self._ids_lock = threading.Lock()
        self.last_send_time = time.time()
        self.last_upload_time = 0.0
        self.transmission_delay = 0.0  # second
        self.package_loss_rate = 0.0  # 0-100 %
        self.sub_forwarding_queue = Queue()
        self._queue_lock = threading.Lock()
        self._send_lock = threading.Lock()
        self.heartbeat_thread = threading.Thread(target=self.heartbeat)
        self.heartbeat_thread.start()
        self.sub_forwarding_thread = threading.Thread(target=self.sub_forwarding)
        self.sub_forwarding_thread.start()

    def _delay_packet_loss_rate(self):
        delay = 0.0
        delay_cnt = 0
        package_loss_rate = 0.0
        package_len = len(self.passed_ids)
        invalid_keys = []

        with self._ids_lock:
            for key, val in self.passed_ids.items():
                if val[1] >= 0:
                    delay += val[1]
                    delay_cnt += 1
                if time.time() - val[0] > 5:  # keep 5 second for each msg
                    invalid_keys.append(key)
                    package_loss_rate += 1

        with self._ids_lock:
            for key in invalid_keys:
                del self.passed_ids[key]

        if delay_cnt > 0:
            delay = delay / delay_cnt
        self.transmission_delay = delay
        if package_len > 0:
            package_loss_rate = package_loss_rate / package_len
        self.package_loss_rate = package_loss_rate

    def heartbeat(self):
        while self.running:
            try:
                hb_msg = get_all_msg_types()['_sys_msgs::HeartBeat'].copy()
                if time.time() - self.last_send_time >= 1.0:
                    with self._send_lock:
                        self.client_socket.sendall(encode_msg(hb_msg))
                    self.last_send_time = time.time()
                if self.pub_type is not None:  # self.pub_suspended
                    all_topics = get_public_topic()
                    url = all_topics['from_key'][self.client_key]['url']
                    if len(all_topics['from_topic'][url]['subs']) > 0:
                        unsuspend_msg = get_all_msg_types()['_sys_msgs::Unsuspend'].copy()
                        with self._send_lock:
                            self.client_socket.sendall(encode_msg(unsuspend_msg))
                        self.last_send_time = time.time()
                        self.pub_suspended = False
                if self.sub_type is not None:  # catch delay issue
                    self._delay_packet_loss_rate()
            except Exception as e:
                logger.error("(ID: {}, P: {}, S: {}) Pipeline->heartbeat: {}".format(
                    self.client_key, self.pub_type, self.sub_url, e))
                self.running = False

            if not self.running and not self._quit:
                logger.info('Quit by heartbeat')
                self.quit()
                self._server.quit(self.client_key)

            time.sleep(1)

    def sub_forwarding(self):
        while self.running:
            while not self.sub_forwarding_queue.empty():
                try:
                    with self._queue_lock:
                        topic = self.sub_forwarding_queue.get()

                    if not self.sub_suspended and (
                            time.time() - self.last_upload_time > self.transmission_delay * 0.3 or self.pub_enforce):
                        self.pass_id += 1
                        passed_msg = get_all_msg_types()['_sys_msgs::TopicDown'].copy()
                        passed_msg['id'] = self.pass_id
                        passed_msg['topic'] = topic
                        with self._ids_lock:
                            self.passed_ids[self.pass_id] = [time.time(), -1]  # Now, Delay
                        with self._send_lock:
                            self.client_socket.sendall(encode_msg(passed_msg))
                        self.last_send_time = time.time()
                        self.last_upload_time = time.time()
                except Exception as e:
                    logger.error("(ID: {}, P: {}, S: {}) Pipeline->sub_forwarding: {}".format(
                        self.client_key, self.pub_type, self.sub_url, e))
                    self.running = False
                    break

            if not self.running and not self._quit:
                logger.info('Quit by sub_forwarding')
                self.quit()
                self._server.quit(self.client_key)

            time.sleep(0.002)

    def sub_forwarding_topic(self, topic: dict):
        # print(self.transmission_delay)
        if self.running and not self.sub_suspended:
            with self._queue_lock:
                self.sub_forwarding_queue.put(topic)

    def _pub_forwarding_topic(self, topic: dict):
        all_topics = get_public_topic()
        url = all_topics['from_key'][self.client_key]['url']
        if len(all_topics['from_topic'][url]['subs']) == 0:
            suspend_msg = get_all_msg_types()['_sys_msgs::Suspend'].copy()
            with self._send_lock:
                self.client_socket.sendall(encode_msg(suspend_msg))
            self.last_send_time = time.time()
            self.pub_suspended = True

        # enc_msg = encode_msg(topic)
        # print(topic)
        for sub in all_topics['from_topic'][url]['subs']:
            self._server.msg_forwarding(sub, topic)

    def _parse_msg(self, data: bytes):
        response = get_all_msg_types()['_sys_msgs::Result'].copy()
        no_reply = False
        success, msg = decode_msg(data)
        if success:
            if '_sys_msgs::Publisher' == msg['type']:
                if 'topic_type' in msg and 'url' in msg:
                    error = check_publish_url_type(msg['url'], msg['topic_type'], self.client_key)
                    if self.sub_type is not None:
                        error = 209
                    if error == 0:
                        self.pub_type = msg['topic_type']
                        self.pub_enforce = msg['enforce']
                        update_topic(msg['url'], msg['topic_type'], self.client_key)
                    else:
                        response = ec2msg(error)
                else:
                    response = ec2msg(206)
            elif '_sys_msgs::Subscriber' == msg['type']:
                if 'topic_type' in msg and 'url' in msg:
                    error = check_subscribe_url_type(msg['url'], msg['topic_type'])
                    if self.pub_type is not None:
                        error = 209
                    if error == 0:
                        self.sub_type = msg['topic_type']
                        self.sub_url = msg['url']
                        if not self.sub_suspended:
                            update_subscriber(self.sub_url, self.sub_type, self.client_key)
                    else:
                        response = ec2msg(error)
                else:
                    response = ec2msg(206)
            elif '_sys_msgs::Suspend' == msg['type'] and self.sub_type is not None:
                self.sub_suspended = True
                remove_subscriber(self.client_key)
                no_reply = True
            elif '_sys_msgs::Unsuspend' == msg['type'] and self.sub_type is not None:
                self.sub_suspended = False
                update_subscriber(self.sub_url, self.sub_type, self.client_key)
                no_reply = True
            elif '_sys_msgs::SmsTopicList' == msg['type']:
                response['error_code'] = 0
                url_types = []
                for key, val in get_public_topic()['from_topic'].items():
                    url_types.append(key + "," + val['type'] + "," + str(len(val['subs'])))
                response['data'] = ";".join(url_types)
            elif '_sys_msgs::TopicUpload' == msg['type']:
                response['id'] = msg['id']
                # response['data'] = msg['timestamp']
                if self.pub_type is None:
                    response = ec2msg(207)
                elif 'topic' in msg and 'type' in msg['topic'] and msg['topic']['type'] == self.pub_type:
                    self._pub_forwarding_topic(msg['topic'])
                else:
                    response = ec2msg(208)
            elif '_sys_msgs::Result' == msg['type']:
                with self._ids_lock:
                    if self.sub_type is not None and msg['id'] in self.passed_ids:
                        recv_id = msg['id']
                        self.passed_ids[recv_id][1] = time.time() - self.passed_ids[recv_id][0]
                no_reply = True
            else:
                no_reply = True
        else:
            response = ec2msg(101)
            logger.debug(data)

        if not no_reply:
            with self._send_lock:
                self.client_socket.sendall(encode_msg(response))
            self.last_send_time = time.time()

    def run(self):
        data = b''
        last_data = b''
        big_msg = 0
        while self.running:
            # tt1 = time.time()
            try:
                data = self.client_socket.recv(1024 * 1024)  # 64K, 65536
                if not data:
                    raise TimeoutError('No data arrived.')
                # print(data)
            except TimeoutError as e:
                logger.error("(ID: {}, P: {}, S: {}) Pipeline->run->recv(1): {}".format(
                    self.client_key, self.pub_type, self.sub_url, e))
                # print(time.time() - tt1)
                self.running = False
                break
            except Exception as e:
                logger.error("(ID: {}, P: {}, S: {}) Pipeline->run->recv(2): {}".format(
                    self.client_key, self.pub_type, self.sub_url, e))
                self.running = False
                break

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
                logger.error("(ID: {}, P: {}, S: {}) Pipeline->run->parse: {}".format(
                    self.client_key, self.pub_type, self.sub_url, e))
                self.running = False

        if not self.running and not self._quit:
            logger.info('Quit by run')
            self.quit()
            self._server.quit(self.client_key)

    def quit(self):
        if not self._quit:
            try:
                if self.sub_type is not None:
                    remove_subscriber(self.client_key)
                self.client_socket.close()
                self._quit = True
            except Exception as e:
                logger.error("(ID: {}, P: {}, S: {}) Pipeline->quit: {}".format(
                    self.client_key, self.pub_type, self.sub_url, e))
            finally:
                self._quit = True

    def is_running(self) -> bool:
        return self.running


class Server(threading.Thread):
    def __init__(self, port=9094):
        threading.Thread.__init__(self)
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        self.listening = False
        self.connected_clients = dict()
        self._clients_lock = threading.Lock()

    def listen(self):
        self.socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.socket_server.settimeout(5)
        self.socket_server.bind(('', self.port))
        self.socket_server.listen(4096)
        logger.info('Start listening on port {} ...'.format(self.port))
        self.listening = True
        self.start()

    def run(self):
        while self.listening:
            try:
                client_socket, client_address = self.socket_server.accept()
                client_socket.settimeout(10)
                client_key = random_vcode()
                while client_key in self.connected_clients.keys():
                    client_key = random_vcode()

                pipeline = Pipeline(client_key, client_socket, self)
                with self._clients_lock:
                    self.connected_clients[client_key] = pipeline
                pipeline.start()
                logger.info('Got client: [{}], ip: {}, port: {}, n_clients: {}'.format(
                    client_key, client_address[0], client_address[1], len(self.connected_clients)))
            except Exception as e:
                logger.error("Server->run: {}".format(e))

    def msg_forwarding(self, client_key: str, topic: dict):
        if client_key in self.connected_clients:
            if self.connected_clients[client_key].is_running():
                self.connected_clients[client_key].sub_forwarding_topic(topic)
            else:
                self.quit(client_key)

    def quit(self, client_key=None):
        try:
            if client_key is None:
                for k, c in self.connected_clients.items():
                    c.quit()
                self.listening = False
            else:
                remove_topic(client_key)
                # show_topic_list()
                self.connected_clients[client_key].quit()
                with self._clients_lock:
                    del self.connected_clients[client_key]
        except Exception as e:
            logger.error("Server->quit: {}".format(e))

        logger.info("Now clients remain: {}, {}".format(
            len(self.connected_clients),
            list(self.connected_clients.keys())
        ))


if __name__ == '__main__':
    server = Server(9094)
    server.listen()
    server.join()
