#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-08-03

import socket
import threading
import time
from queue import Queue
from spirems.log import get_logger
from spirems.msg_helper import (get_all_msg_types, def_msg, encode_msg, check_topic_url, decode_msg, check_msg,
                                index_msg_header, decode_msg_header, check_node_name, can_be_jsonified)
from spirems.error_code import ec2str

logger = get_logger('Parameter')


class Parameter(threading.Thread):

    def __init__(self, node_name: str, callback_func: callable, ip: str = '127.0.0.1', port: int = 9094):
        threading.Thread.__init__(self)
        self.node_name = node_name
        self.ip = ip
        self.port = port
        self.callback_func = callback_func
        self.param_queue = Queue()
        self.sync_params = {}
        self._send_lock = threading.Lock()

        all_types = get_all_msg_types()
        state = check_node_name(self.node_name)
        if state != 0:
            raise ValueError('{}, please verify...'.format(ec2str(state)))

        self.last_send_time = 0.0
        self.force_quit = False
        self.heartbeat_thread = None
        self.heartbeat_running = False
        self.running = True
        try:
            self._link()
        except Exception as e:
            logger.warning("({}) __init__: {}".format(self.node_name, e))
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
            try:
                if time.time() - self.last_send_time >= 1.0:
                    apply_topic = def_msg('_sys_msgs::Parameter')
                    apply_topic['node_name'] = self.node_name
                    with self._send_lock:
                        self.client_socket.sendall(encode_msg(apply_topic))
                    self.last_send_time = time.time()
            except Exception as e:
                logger.warning("({}) heartbeat: {}".format(self.node_name, e))

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

    def get_param(self, param_key: str):
        _params_ret = self.get_params([param_key])
        if param_key in _params_ret:
            return _params_ret[param_key]
        else:
            return None

    def get_all_params(self) -> dict:
        if self.node_name == '_global':
            return self.get_params([])
        else:
            return self.sync_params

    def get_params(self, params_keys: list[str]) -> dict:
        assert isinstance(params_keys, list), "The input params_keys must be a list type!"
        for param_key in params_keys:
            assert isinstance(param_key, str), "The input param_key must be a string type!"
        while not (self.running and self.heartbeat_running):
            time.sleep(0.1)
        if self.running and self.heartbeat_running:
            try:
                pr_msg = def_msg('_sys_msgs::ParamReader')
                pr_msg['keys'] = params_keys
                with self._send_lock:
                    self.client_socket.sendall(encode_msg(pr_msg))
                self.last_send_time = time.time()

                params_ret = self.param_queue.get(block=True)
                self.sync_params.update(params_ret)
                return params_ret
            except Exception as e:
                logger.warning("({}) ParamReader: {}".format(self.node_name, e))
        return {}

    def set_param(self, param_key: str, param_value: any):
        self.set_params({param_key: param_value})

    def set_params(self, params_dict: dict):
        for param_key, param_val in params_dict.items():
            assert isinstance(param_key, str), "The input param_key must be a string type!"
            assert can_be_jsonified(param_val), "The input param_value must be jsonified!"
        while not (self.running and self.heartbeat_running):
            time.sleep(0.1)
        if self.running and self.heartbeat_running:
            try:
                pw_msg = def_msg('_sys_msgs::ParamWriter')
                pw_msg['params'] = params_dict
                self.sync_params.update(params_dict)
                with self._send_lock:
                    self.client_socket.sendall(encode_msg(pw_msg))
                self.last_send_time = time.time()

            except Exception as e:
                logger.warning("({}) ParamWriter: {}".format(self.node_name, e))

    def _parse_msg(self, msg):
        success, decode_data = decode_msg(msg)
        if success and decode_data['type'] == '_sys_msgs::Result':
            if decode_data['error_code'] != 0:
                logger.error(decode_data['data'])
            else:
                if 'params' in decode_data:
                    if self.node_name == '_global':
                        self.param_queue.put(decode_data['params'])
                    else:
                        received_params = {}
                        n_prefix = '/' + self.node_name + '/'
                        g_prefix = '/_global'
                        for param_key in decode_data['params'].keys():
                            if param_key.startswith(n_prefix):
                                received_params[param_key[len(n_prefix):]] = decode_data['params'][param_key]
                            elif param_key.startswith(g_prefix):
                                received_params[param_key[len(g_prefix):]] = decode_data['params'][param_key]
                        self.param_queue.put(received_params)
        elif success and decode_data['type'] == '_sys_msgs::TopicDown':
            received_params = {}
            n_prefix = '/' + self.node_name + '/'
            g_prefix = '/_global'
            for param_key in decode_data['topic'].keys():
                if param_key.startswith(n_prefix):
                    received_params[param_key[len(n_prefix):]] = decode_data['topic'][param_key]
                elif param_key.startswith(g_prefix):
                    received_params[param_key[len(g_prefix):]] = decode_data['topic'][param_key]
            self.sync_params.update(received_params)
            self.callback_func(received_params)
        elif not success:
            logger.debug(msg)

    def run(self):
        data = b''
        last_data = b''
        big_msg = 0
        while self.running:
            if self.force_quit:
                self.running = False
                break
            try:
                data = self.client_socket.recv(1024 * 1024)  # 64K, 65536
                if not data:
                    raise TimeoutError('No data arrived.')
                # print('data: {}'.format(data))
            except TimeoutError as e:
                logger.warning("({}) recv(1): {}".format(self.node_name, e))
                # print(time.time() - tt1)
                self.running = False
                data = b''
            except Exception as e:
                logger.warning("({}) recv(2): {}".format(self.node_name, e))
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
                logger.warning("({}) parse: {}".format(self.node_name, e))
                self.running = False

            while not self.running:
                if self.force_quit:
                    break
                # logger.info('(1) running=False, heartbeat_running=False')
                self.heartbeat_running = False
                try:
                    self.client_socket.close()
                    # logger.info('(2) client_socket closed')
                except Exception as e:
                    logger.warning("({}) socket_close: {}".format(self.node_name, e))
                time.sleep(5)
                # logger.info('(3) start re-linking ...')
                try:
                    self._link()
                    self.running = True
                    # logger.info('(4) running=True, suspended=False')
                except Exception as e:
                    logger.warning("({}) relink: {}".format(self.node_name, e))
                logger.info('Running={}, Wait ...'.format(self.running))
                data = b''
                last_data = b''
                big_msg = 0


def params_changed(msg):
    print(params_changed, msg)


if __name__ == '__main__':
    param = Parameter('DetNode', params_changed)
    param.set_param('/dataset', ['ass', 1232])
    param.set_params({'my_param1': 123, 'my_param2': '456'})
    # print(param.get_params(['123', 123]))
    param.join()
