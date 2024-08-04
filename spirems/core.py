#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import math
import threading
import socket
import random
import time
import struct
from queue import Queue
from spirems.log import get_logger
from spirems.msg_helper import (get_all_msg_types, index_msg_header, decode_msg_header, decode_msg, encode_msg,
                                check_topic_url, check_msg, check_node_name, def_msg, check_param_key,
                                check_global_param_key)
from spirems.error_code import ec2msg


logger = get_logger('Core')


def singleton(cls):
    _instance = None
    _lock = threading.Lock()

    def wrapper(*args, **kwargs):
        nonlocal _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls(*args, **kwargs)
        return _instance

    return wrapper


@singleton
class SpireMS:
    def __init__(self):
        self.m_topic_list = {
            'from_topic': {},
            'from_key': {},
            'from_subscriber': {}
        }
        self.m_topic_list_lock = threading.Lock()
        self.m_params = {}
        self.m_params_lock = threading.Lock()
        self.m_nodes = {}
        self.m_nodes_lock = threading.Lock()

    def is_param_exist(self, param: str) -> bool:
        return param in self.m_params

    def get_all_params(self) -> dict:
        with self.m_params_lock:
            all_params = {}
            for key, value in self.m_params.items():
                all_params[key] = value['value']
            return all_params

    def get_param(self, param: str) -> dict:
        with self.m_params_lock:
            if param in self.m_params:
                return {param: self.m_params[param]['value']}
            else:
                return {}

    def update_param(self, param: str, value, client_key: str) -> set:
        with self.m_params_lock:
            if param in self.m_params:
                self.m_params[param]['client_keys'].add(client_key)
                self.m_params[param]['value'] = value
            else:
                self.m_params[param] = {
                    'client_keys': {client_key},
                    'value': value
                }
            return self.m_params[param]['client_keys'].copy()

    def is_param_node_exist(self, node_name: str, client_key: str) -> bool:
        with self.m_nodes_lock:
            return node_name in self.m_nodes and self.m_nodes[node_name] != client_key

    def add_param_node(self, node_name: str, client_key: str):
        with self.m_nodes_lock:
            if node_name not in self.m_nodes:
                self.m_nodes[node_name] = client_key

    def add_global_param_node(self, client_key: str):
        with self.m_params_lock:
            for param in self.m_params:
                self.m_params[param]['client_keys'].add(client_key)

    def remove_param_node(self, node_name: str, client_key: str):
        with self.m_nodes_lock:
            if node_name in self.m_nodes:
                del self.m_nodes[node_name]
        with self.m_params_lock:
            for param in self.m_params:
                self.m_params[param]['client_keys'].discard(client_key)
                if len(self.m_params[param]['client_keys']) == 0:
                    del self.m_params[param]

    def get_public_topic_list(self) -> list:
        with self.m_topic_list_lock:
            urls = list(self.m_topic_list['from_topic'].keys())
        urls.sort()
        return urls

    def get_public_topic(self) -> dict:
        with self.m_topic_list_lock:
            return self.m_topic_list.copy()

    def sync_topic_subscriber(self):
        with self.m_topic_list_lock:
            for topic in self.m_topic_list['from_topic'].keys():
                self.m_topic_list['from_topic'][topic]['subs'] = []
            for client_key, client in self.m_topic_list['from_subscriber'].items():
                if client['url'] in self.m_topic_list['from_topic']:
                    if client['type'] == self.m_topic_list['from_topic'][client['url']]['type']:
                        self.m_topic_list['from_topic'][client['url']]['subs'].append(client_key)
                    elif client['type'] == 'std_msgs::Null':
                        self.m_topic_list['from_topic'][client['url']]['subs'].append(client_key)

    def remove_topic(self, client_key: str):
        with self.m_topic_list_lock:
            if client_key in self.m_topic_list['from_key']:
                url = self.m_topic_list['from_key'][client_key]['url']
                if client_key in self.m_topic_list['from_topic'][url]['key']:
                    del self.m_topic_list['from_topic'][url]['key'][
                        self.m_topic_list['from_topic'][url]['key'].index(client_key)
                    ]
                if not self.m_topic_list['from_topic'][url]['key']:
                    del self.m_topic_list['from_topic'][url]
                del self.m_topic_list['from_key'][client_key]
        self.sync_topic_subscriber()

    def remove_subscriber(self, client_key: str):
        with self.m_topic_list_lock:
            if client_key in self.m_topic_list['from_subscriber']:
                del self.m_topic_list['from_subscriber'][client_key]
        self.sync_topic_subscriber()

    def update_topic(self, topic_url: str, topic_type: str, client_key: str):
        with self.m_topic_list_lock:
            if client_key not in self.m_topic_list['from_key']:
                self.m_topic_list['from_key'][client_key] = {
                    'url': topic_url,
                    'type': topic_type,
                    'key': client_key
                }
                if topic_url in self.m_topic_list['from_topic']:
                    self.m_topic_list['from_topic'][topic_url]['key'].append(client_key)
                else:
                    self.m_topic_list['from_topic'][topic_url] = {
                        'url': topic_url,
                        'type': topic_type,
                        'key': [client_key]
                    }
        self.sync_topic_subscriber()

    def update_subscriber(self, topic_url: str, topic_type: str, client_key: str):
        with self.m_topic_list_lock:
            if client_key not in self.m_topic_list['from_subscriber']:
                self.m_topic_list['from_subscriber'][client_key] = {
                    'url': topic_url,
                    'type': topic_type,
                    'key': client_key
                }
        self.sync_topic_subscriber()


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


def check_parameter_node_name(node_name: str) -> int:
    error = check_node_name(node_name)
    return error


def random_vcode(k=6):
    vcode = ''.join(random.choices(
        ['z', 'y', 'x', 'w', 'v', 'u', 't', 's', 'r', 'q', 'p', 'o', 'n', 'm', 'l', 'k', 'j', 'i', 'h', 'g', 'f', 'e',
         'd', 'c', 'b', 'a', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9'], k=k))
    return vcode


class Pipeline(threading.Thread):
    def __init__(self, client_key: str, client_socket, _server):
        threading.Thread.__init__(self)
        self.client_key = client_key
        self.client_socket = client_socket
        self._server = _server
        self.running = True
        self.pub_type = None
        self.pub_enforce = True
        self.sub_type = None
        self.sub_url = None
        self.param_node_name = None
        self.param_node_on = False
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
                hb_msg = def_msg('_sys_msgs::HeartBeat')
                if time.time() - self.last_send_time >= 1.0:
                    with self._send_lock:
                        self.client_socket.sendall(encode_msg(hb_msg))
                    self.last_send_time = time.time()
                if self.pub_type is not None:  # self.pub_suspended
                    all_topics = SpireMS().get_public_topic()
                    url = all_topics['from_key'][self.client_key]['url']
                    if len(all_topics['from_topic'][url]['subs']) > 0:
                        unsuspend_msg = def_msg('_sys_msgs::Unsuspend')
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
            try:
                topic = self.sub_forwarding_queue.get(block=True)
                if topic is None:
                    raise EOFError('Topic is None.')

                if not self.sub_suspended and (
                        time.time() - self.last_upload_time > self.transmission_delay * 0.3 or self.pub_enforce):
                    self.pass_id += 1
                    if self.pass_id > 1e6:
                        self.pass_id = 1
                    passed_msg = def_msg('_sys_msgs::TopicDown')
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

    def sub_forwarding_topic(self, topic: dict):
        # print(self.transmission_delay)
        if self.running and not self.sub_suspended:
            self.sub_forwarding_queue.put(topic)

    def _pub_forwarding_topic(self, topic: dict):
        all_topics = SpireMS().get_public_topic()
        url = all_topics['from_key'][self.client_key]['url']
        if len(all_topics['from_topic'][url]['subs']) == 0:
            suspend_msg = def_msg('_sys_msgs::Suspend')
            with self._send_lock:
                self.client_socket.sendall(encode_msg(suspend_msg))
            self.last_send_time = time.time()
            self.pub_suspended = True

        # enc_msg = encode_msg(topic)
        # print(topic)
        for sub in all_topics['from_topic'][url]['subs']:
            self._server.msg_forwarding(sub, topic)

    def _parse_msg(self, data: bytes):
        response = def_msg('_sys_msgs::Result')
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
                        SpireMS().update_topic(msg['url'], msg['topic_type'], self.client_key)
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
                            SpireMS().update_subscriber(self.sub_url, self.sub_type, self.client_key)
                    else:
                        response = ec2msg(error)
                else:
                    response = ec2msg(206)
            elif '_sys_msgs::Parameter' == msg['type']:
                if 'node_name' in msg:
                    error = check_parameter_node_name(msg['node_name'])
                    if self.pub_type is not None or self.sub_type is not None:
                        error = 213
                    if SpireMS().is_param_node_exist(msg['node_name'], self.client_key):
                        error = 214
                    if error == 0:
                        if not self.param_node_on:
                            if msg['node_name'] == '_global':
                                SpireMS().add_global_param_node(self.client_key)
                            else:
                                SpireMS().add_param_node(msg['node_name'], self.client_key)
                            self.param_node_name = msg['node_name']
                            self.param_node_on = True
                    else:
                        response = ec2msg(error)
                else:
                    response = ec2msg(212)
            elif '_sys_msgs::Suspend' == msg['type'] and self.sub_type is not None:
                self.sub_suspended = True
                SpireMS().remove_subscriber(self.client_key)
                no_reply = True
            elif '_sys_msgs::Unsuspend' == msg['type'] and self.sub_type is not None:
                self.sub_suspended = False
                SpireMS().update_subscriber(self.sub_url, self.sub_type, self.client_key)
                no_reply = True
            elif '_sys_msgs::SmsTopicList' == msg['type']:
                response['error_code'] = 0
                url_types = []
                for key, val in SpireMS().get_public_topic()['from_topic'].items():
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
            elif '_sys_msgs::ParamWriter' == msg['type']:
                if self.param_node_name is not None:
                    client_key_with_params = dict()
                    if self.param_node_name == '_global':
                        for param_key in msg['params'].keys():
                            param_err = check_global_param_key(param_key)
                            if 0 == param_err:
                                if SpireMS().is_param_exist(param_key):
                                    client_keys = SpireMS().update_param(
                                        param_key, msg['params'][param_key], self.client_key)
                                    for client_key in client_keys:
                                        if client_key not in client_key_with_params:
                                            client_key_with_params[client_key] = dict()
                                        client_key_with_params[client_key][param_key] = msg['params'][param_key]
                                else:
                                    response = ec2msg(223)
                            else:
                                response = ec2msg(param_err)
                    else:
                        for param_key in msg['params'].keys():
                            param_err = check_param_key(param_key)
                            if 0 == param_err:
                                if param_key.startswith('/'):
                                    abs_param_key = '/_global' + param_key
                                else:
                                    abs_param_key = '/' + self.param_node_name + '/' + param_key
                                client_keys = SpireMS().update_param(
                                    abs_param_key, msg['params'][param_key], self.client_key)
                                for client_key in client_keys:
                                    if client_key not in client_key_with_params:
                                        client_key_with_params[client_key] = dict()
                                    client_key_with_params[client_key][abs_param_key] = msg['params'][param_key]
                            else:
                                response = ec2msg(param_err)
                    for client_key in client_key_with_params:
                        self._server.msg_forwarding(client_key, client_key_with_params[client_key])
                else:
                    response = ec2msg(215)
            elif '_sys_msgs::ParamReader' == msg['type']:
                if self.param_node_name is not None:
                    params = dict()
                    if self.param_node_name == '_global':
                        if len(msg['keys']):
                            for param_key in msg['keys']:
                                params.update(SpireMS().get_param(param_key))
                        else:
                            params.update(SpireMS().get_all_params())
                    else:
                        for param_key in msg['keys']:
                            if param_key.startswith('/'):
                                params.update(SpireMS().get_param('/_global' + param_key))
                            else:
                                params.update(SpireMS().get_param('/' + self.param_node_name + '/' + param_key))
                    response['params'] = params
                else:
                    response = ec2msg(215)
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
                self.sub_forwarding_queue.put(None)
                if self.sub_type is not None:
                    SpireMS().remove_subscriber(self.client_key)
                if self.param_node_name is not None:
                    SpireMS().remove_param_node(self.param_node_name, self.client_key)
                self.client_socket.close()
            except Exception as e:
                logger.error("(ID: {}, P: {}, S: {}) Pipeline->quit: {}".format(
                    self.client_key, self.pub_type, self.sub_url, e))
            finally:
                self._quit = True

    def is_running(self) -> bool:
        return self.running


class Core(threading.Thread):
    def __init__(self, port=9094):
        threading.Thread.__init__(self)
        self.socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.port = port
        self.listening = False
        self.connected_clients = dict()
        self._clients_lock = threading.Lock()
        self.listen()

    def is_port_available(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', self.port))
            return True
        except OSError:
            return False

    def listen(self):
        if not self.is_port_available():
            logger.error('The port {} is already used. Please check!'.format(self.port))
            return
        self.socket_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.socket_server.settimeout(5)
        self.socket_server.bind(('', self.port))
        self.socket_server.listen(4096)
        spirems_pattern = \
"""
Welcome to:

  o-o                 o   o  o-o  
 |          o         |\ /| |     
  o-o  o-o    o-o o-o | O |  o-o  
     | |  | | |   |-' | | |     | 
 o--o  O-o  | o   o-o o o o o--o  
       |                          
       o                          
"""
        logger.info(spirems_pattern)
        logger.info('Start on port {} ...'.format(self.port))
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
                SpireMS().remove_topic(client_key)
                self.connected_clients[client_key].quit()
        except Exception as e:
            logger.error("Server->quit: {}".format(e))
        finally:
            with self._clients_lock:
                if client_key in self.connected_clients:
                    del self.connected_clients[client_key]

        logger.info("Now clients remain: {}, {}".format(
            len(self.connected_clients),
            list(self.connected_clients.keys())
        ))


def main():
    server = Core(9094)
    try:
        server.join()
    except:
        pass


if __name__ == '__main__':
    main()
