#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import threading
import socket
import random
import time
import re
from log import get_logger
from msg_helper import (get_all_msg_types, index_msg_header, decode_msg_header, decode_msg, encode_msg,
                        check_topic_url, check_msg)
from error_code import ec2msg


logger = get_logger('Server')
TOPIC_LIST = None


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
        del topic_list['from_topic'][url]
        del topic_list['from_key'][client_key]
        sync_topic_subscriber()


def remove_subscriber(client_key: str):
    topic_list = get_public_topic()
    if client_key in topic_list['from_subscriber']:
        del topic_list['from_subscriber'][client_key]
        sync_topic_subscriber()


def update_topic(topic_url: str, topic_type: str, client_key: str):
    topic_list = get_public_topic()
    if client_key in topic_list['from_key']:
        remove_topic(client_key)
    topic_list['from_key'][client_key] = {
        'url': topic_url,
        'type': topic_type,
        'key': client_key
    }
    topic_list['from_topic'][topic_url] = {
        'url': topic_url,
        'type': topic_type,
        'key': client_key
    }
    sync_topic_subscriber()


def update_subscriber(topic_url: str, topic_type: str, client_key: str):
    topic_list = get_public_topic()
    if client_key in topic_list['from_subscriber']:
        remove_subscriber(client_key)
    topic_list['from_subscriber'][client_key] = {
        'url': topic_url,
        'type': topic_type,
        'key': client_key
    }
    sync_topic_subscriber()


def check_publish_url_type(topic_url: str, topic_type: str) -> int:
    error = check_topic_url(topic_url)
    if topic_url in get_public_topic()['from_topic']:
        error = 204  # As the same as the existing
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
        self.sub_type = None
        self._quit = False
        self.pub_suspended = False
        self.last_msg_err = False
        heartbeat_thread = threading.Thread(target=self.heartbeat)
        heartbeat_thread.start()

    def heartbeat(self):
        while self.running:
            hb_msg = get_all_msg_types()['_sys_msgs::HeartBeat'].copy()
            try:
                self.client_socket.send(encode_msg(hb_msg))
                if self.pub_suspended:
                    all_topics = get_public_topic()
                    url = all_topics['from_key'][self.client_key]['url']
                    if len(all_topics['from_topic'][url]['subs']) > 0:
                        unsuspend_msg = get_all_msg_types()['_sys_msgs::Unsuspend'].copy()
                        self.client_socket.send(encode_msg(unsuspend_msg))
                        self.pub_suspended = False
                time.sleep(1)
            except Exception as e:
                logger.error("heartbeat: {}".format(e))
                self.running = False

            if not self.running and not self._quit:
                logger.info('Quit by heartbeat')
                self.quit()
                self._server.quit(self.client_key)

    def _forwarding_topic(self, topic: dict):
        all_topics = get_public_topic()
        url = all_topics['from_key'][self.client_key]['url']
        if len(all_topics['from_topic'][url]['subs']) == 0:
            suspend_msg = get_all_msg_types()['_sys_msgs::Suspend'].copy()
            self.client_socket.send(encode_msg(suspend_msg))
            self.pub_suspended = True

        enc_msg = encode_msg(topic)
        for sub in all_topics['from_topic'][url]['subs']:
            try:
                self._server.msg_forwarding(sub, enc_msg)
            except Exception as e:
                logger.debug('ForwardException: {}'.format(e))

    def _parse_msg(self, data: bytes):
        response = get_all_msg_types()['_sys_msgs::Result'].copy()
        success, msg = decode_msg(data)
        if success:
            if '_sys_msgs::Publisher' == msg['type']:
                if 'topic_type' in msg and 'url' in msg:
                    error = check_publish_url_type(msg['url'], msg['topic_type'])
                    if self.sub_type is not None:
                        error = 209
                    if error == 0:
                        self.pub_type = msg['topic_type']
                        update_topic(msg['url'], msg['topic_type'], self.client_key)
                        # show_topic_list()
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
                        update_subscriber(msg['url'], msg['topic_type'], self.client_key)
                    else:
                        response = ec2msg(error)
                else:
                    response = ec2msg(206)
            elif '_sys_msgs::SmsTopicList' == msg['type']:
                response['error_code'] = 0
                url_types = []
                for key, val in get_public_topic()['from_topic'].items():
                    url_types.append(key + "," + val['type'])
                response['data'] = ";".join(url_types)
                print(response)
            elif '_sys_msgs::TopicUpload' == msg['type']:
                if self.pub_type is None:
                    response = ec2msg(207)
                elif 'topic' in msg and 'type' in msg['topic'] and msg['topic']['type'] == self.pub_type:
                    # logger.debug(encode_msg(msg['topic'])[8:])
                    self._forwarding_topic(msg['topic'])
                else:
                    response = ec2msg(208)
        else:
            response = ec2msg(101)
            logger.debug(data)

        self.client_socket.send(encode_msg(response))

    def run(self):
        data = b''
        last_data = b''
        big_msg = 0
        while self.running:
            try:
                data = self.client_socket.recv(4096)
            except socket.timeout:
                pass

            try:
                checked_msgs, parted_msg, parted_len = check_msg(data)

                if len(parted_msg) > 0:
                    if parted_len > 0:
                        last_data = parted_msg
                        big_msg = parted_len
                    else:
                        last_data += parted_msg
                        if 0 < big_msg <= len(last_data):
                            checked_msgs.append(last_data[:big_msg])
                            big_msg = 0
                            last_data = b''

                if len(checked_msgs) > 0:
                    for msg in checked_msgs:
                        self._parse_msg(msg)

            except Exception as e:
                logger.error(e)
                self.running = False

        if not self.running and not self._quit:
            logger.info('Quit by run')
            self.quit()
            self._server.quit(self.client_key)

    def quit(self):
        if not self._quit:
            if self.sub_type is not None:
                remove_subscriber(self.client_key)
            self.client_socket.close()
            self._quit = True


class Server(threading.Thread):
    def __init__(self, port=9000):
        threading.Thread.__init__(self)
        socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        socket_server.settimeout(5)
        socket_server.bind(('', port))
        socket_server.listen(512)

        logger.info('Start listening on port {} ...'.format(port))
        self.socket_server = socket_server
        self.listening = True
        self.connected_clients = dict()

    def run(self):
        while self.listening:
            try:
                client_socket, client_address = self.socket_server.accept()
                client_socket.settimeout(5)
                client_key = random_vcode()
                while client_key in self.connected_clients.keys():
                    client_key = random_vcode()
                logger.info('Got client: [{}], ip: {}, port: {}'.format(client_key, client_address[0], client_address[1]))

                pipeline = Pipeline(client_key, client_socket, self)
                self.connected_clients[client_key] = pipeline
                pipeline.start()
            except socket.timeout:
                pass

    def msg_forwarding(self, client_key: str, msg: bytes):
        if client_key in self.connected_clients:
            self.connected_clients[client_key].client_socket.send(msg)

    def quit(self, client_key=None):
        if client_key is None:
            for k, c in self.connected_clients.items():
                c.quit()
            self.listening = False
        else:
            try:
                remove_topic(client_key)
                # show_topic_list()
                self.connected_clients[client_key].quit()
                del self.connected_clients[client_key]
            except Exception as e:
                pass
        logger.info("Now clients remain: {}, {}".format(
            len(self.connected_clients),
            list(self.connected_clients.keys())
        ))


if __name__ == '__main__':
    server = Server(9094)
    server.start()
