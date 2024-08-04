#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import os
import json
import struct
import json
import time
import re
from spirems.log import get_logger


logger = get_logger('MsgHelper')
inner_msg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'msgs')
ext_msg_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json_msgs')
ext_schema_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'json_schemas')
ALL_MSG_TYPES = None
ALL_MSG_SCHEMAS = None


def get_all_msg_types() -> dict:
    global ALL_MSG_TYPES
    if ALL_MSG_TYPES is None:
        types = dict()
        msgs_dirs = [inner_msg_dir, ext_msg_dir]
        for msgs_dir in msgs_dirs:
            sub_dirs = os.listdir(msgs_dir)
            for sub_dir in sub_dirs:
                if os.path.isdir(os.path.join(msgs_dir, sub_dir)):
                    json_fs = os.listdir(os.path.join(msgs_dir, sub_dir))
                    for json_f in json_fs:
                        if os.path.splitext(json_f)[-1] == '.json':
                            with open(os.path.join(msgs_dir, sub_dir, json_f), 'r') as file:
                                msg = json.load(file)
                            types[msg['type']] = msg
        ALL_MSG_TYPES = types
    return ALL_MSG_TYPES


def get_all_msg_schemas() -> dict:
    global ALL_MSG_SCHEMAS
    if ALL_MSG_SCHEMAS is None:
        schemas = dict()
        sub_dirs = os.listdir(ext_schema_dir)
        for sub_dir in sub_dirs:
            if os.path.isdir(os.path.join(ext_schema_dir, sub_dir)):
                json_fs = os.listdir(os.path.join(ext_schema_dir, sub_dir))
                for json_f in json_fs:
                    if os.path.splitext(json_f)[-1] == '.json':
                        with open(os.path.join(ext_schema_dir, sub_dir, json_f), 'r') as file:
                            msg = json.load(file)
                        schemas[msg['title']] = msg
        ALL_MSG_SCHEMAS = schemas
    return ALL_MSG_SCHEMAS


get_all_msg_types()
get_all_msg_schemas()


def load_msg_types(msgs_dir: str):
    msg_types = get_all_msg_types()
    sub_dirs = os.listdir(msgs_dir)
    for sub_dir in sub_dirs:
        if os.path.isdir(os.path.join(msgs_dir, sub_dir)):
            json_fs = os.listdir(os.path.join(msgs_dir, sub_dir))
            for json_f in json_fs:
                if os.path.splitext(json_f)[-1] == '.json':
                    with open(os.path.join(msgs_dir, sub_dir, json_f), 'r') as file:
                        msg = json.load(file)
                    if msg['type'] not in msg_types:
                        msg_types[msg['type']] = msg


def def_msg(msg_type: str = 'std_msgs::Null') -> dict:
    msg_types = get_all_msg_types()
    if msg_type in msg_types:
        return msg_types[msg_type].copy()
    else:
        return msg_types['std_msgs::Null'].copy()


def ros_time() -> dict:
    seconds = int(time.time())
    nanoseconds = int(time.time_ns() % 1e9)
    return {'sec': seconds, 'nsec': nanoseconds}


def index_msg_header(data: bytes) -> int:
    if b'\xEA\xEC\xFB\xFD' in data:
        return data.index(b'\xEA\xEC\xFB\xFD')
    else:
        return -1


def decode_msg_header(data: bytes) -> int:
    msg_len = 0
    if len(data) > 8:
        if data[:4] == b'\xEA\xEC\xFB\xFD':
            n_bytes = struct.unpack('i', data[4: 8])[0]
            msg_len = n_bytes + 8
    return msg_len


def check_msg(data: bytes) -> (list, list, list):
    # return checked_msgs, parted_msg
    checked_msgs = []
    parted_msgs = []  # b''
    parted_lens = []  # 0
    msg_len_max = 1024 * 1024 * 50  # 50Mb
    index = index_msg_header(data)
    if index >= 0:
        if index > 0:
            parted_msg = data[:index]
            parted_msgs.append(parted_msg)
            parted_lens.append(0)
        data = data[index:]
        msg_len = decode_msg_header(data)
        if msg_len > 8:
            while len(data) >= msg_len:
                if 8 < msg_len < msg_len_max:
                    checked_msgs.append(data[:msg_len])

                data = data[msg_len:]
                index = index_msg_header(data)
                if index >= 0:
                    data = data[index:]
                    msg_len = decode_msg_header(data)
                    if msg_len <= 8:
                        break
                else:
                    msg_len = 0
                    break
            if 8 < msg_len < msg_len_max:
                parted_msg = data
                parted_len = msg_len
                parted_msgs.append(parted_msg)
                parted_lens.append(parted_len)
    elif len(data) > 0:
        parted_msg = data
        parted_msgs.append(parted_msg)
        parted_lens.append(0)
    return checked_msgs, parted_msgs, parted_lens


def decode_msg(data: bytes) -> (bool, dict):
    success = True
    decode_data = dict()
    if len(data) > 8:
        if data[:4] == b'\xEA\xEC\xFB\xFD':
            n_bytes = struct.unpack('i', data[4: 8])[0]
            if n_bytes == len(data) - 8:
                json_str = data[8:].decode("utf-8")
                try:
                    decode_data = json.loads(json_str)
                    if 'type' not in decode_data.keys():
                        success = False
                except Exception as e:
                    success = False
            else:
                success = False
        else:
            success = False
    else:
        success = False
    return success, decode_data


def encode_msg(data: dict) -> bytes:
    encoded_data = b'\xEA\xEC\xFB\xFD'
    if 'timestamp' in data.keys() and data['timestamp'] == 0.0:
        data['timestamp'] = time.time()
    json_str = json.dumps(data)
    json_len = len(json_str)
    _len = struct.pack('i', json_len)
    encoded_data = encoded_data + _len + json_str.encode("utf-8")
    return encoded_data


def check_topic_url(topic_url: str) -> int:
    error = 0
    pattern = r'^[a-zA-Z0-9_/]*$'
    if len(topic_url) < 2:
        error = 201  # at least 2 chars
    elif not topic_url.startswith('/'):
        error = 202  # need started with '/'
    elif not re.match(pattern, topic_url):
        error = 203  # only to use 'a-z', '0-9', '_' or '/'
    return error


def check_node_name(node_name: str) -> int:
    error = 0
    pattern = r'^[a-zA-Z0-9_]*$'
    if len(node_name) < 2:
        error = 210  # at least 2 chars
    elif not re.match(pattern, node_name):
        error = 211  # only to use 'a-z', '0-9', '_'
    elif node_name.startswith('_'):
        if node_name == '_global':
            pass
        else:
            error = 216
    return error


def check_param_key(param_key: str) -> int:
    error = 0
    pattern = r'^[a-zA-Z0-9_]*$'
    if len(param_key) < 2:
        error = 217  # at least 2 chars
    elif param_key.startswith('/') and not re.match(pattern, param_key[1:]):
        error = 218  # only to use 'a-z', '0-9', '_'
    elif not param_key.startswith('/') and not re.match(pattern, param_key):
        error = 218  # only to use 'a-z', '0-9', '_'
    elif param_key.startswith('_'):
        error = 219
    return error


def check_global_param_key(param_key: str) -> int:
    error = 0
    pattern = r'^[a-zA-Z0-9_/]*$'
    if len(param_key) < 2:
        error = 220  # at least 6 chars
    elif not re.match(pattern, param_key):
        error = 221  # only to use 'a-z', '0-9', '_', '/'
    elif not param_key.startswith('/'):
        error = 222
    return error


if __name__ == '__main__':
    print(check_param_key('_test'))
