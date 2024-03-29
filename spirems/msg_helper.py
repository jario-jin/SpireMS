#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import os
import json
import struct
import json
import time
import re
from log import get_logger


logger = get_logger('MsgHelper')
ALL_MSG_TYPES = None


def get_all_msg_types(msgs_dir: str = './msgs') -> dict:
    global ALL_MSG_TYPES
    if ALL_MSG_TYPES is None:
        types = dict()
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


get_all_msg_types()


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


if __name__ == '__main__':
    # 定义字典
    all_types = get_all_msg_types()
    data = all_types['std_msgs::Number']

    # 使用 json.dumps() 函数将字典转换为 JSON 字符串
    msg = encode_msg(data)
    # msg = 'hello'.encode('utf-8') + msg
    print(index_msg_header(b'\xEA\xEC\xFB\xFD'))
    print(msg[index_msg_header(msg):])
    print(index_msg_header(msg))
    print(decode_msg_header(msg))
    stat, _dict = decode_msg(msg)
    print(stat, _dict)

    all_types = get_all_msg_types()
    for t in all_types.items():
        print(t)
    print(list(all_types.keys()))
