#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

import socket
import time

from spirems.msg_helper import (encode_msg, decode_msg, get_all_msg_types, def_msg, check_msg,
                                index_msg_header, decode_msg_header)
import sys
import argparse
import json
from spirems.subscriber import Subscriber


def _echo(topic, ip, port):
    def _parse_msg(msg):
        formatted_str = json.dumps(msg, indent=4)
        print(formatted_str)

    sub = Subscriber(topic, 'std_msgs::Null', _parse_msg, ip=ip, port=port)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('stopped by keyboard')
        sub.kill()
        sub.join()


t1 = 0
t2 = 0
t3 = 0
min_dt = 1e6
max_dt = 0
cnt = 0


def _hz(topic, ip, port):
    def _parse_msg(msg):
        global t1, t2, t3, min_dt, max_dt, cnt
        cnt += 1
        if t1 == 0:
            t1 = time.time()
            t2 = t1
            t3 = t1
            cnt = 0
        else:
            dt = time.time() - t1
            if dt < min_dt:
                min_dt = dt
            if dt > max_dt:
                max_dt = dt
            t1 = time.time()
            if t1 - t2 > 2:
                t2 = t1
                print("Average Rate: {:.2f}, Max Time Interval: {:.1f} ms, Min Time Interval: {:.1f} ms".format(
                    cnt / (t1 - t3), max_dt * 1000, min_dt * 1000
                ))

    sub = Subscriber(topic, 'std_msgs::Null', _parse_msg, ip=ip, port=port)
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print('stopped by keyboard')
        sub.kill()
        sub.join()


def _list(ip, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(5)
    client_socket.connect((ip, port))

    client_socket.send(encode_msg(def_msg('_sys_msgs::SmsTopicList')))
    columns = ['Topics', 'Type', 'Subscribed-by']

    def _parse_msg(res):
        success, decode_data = decode_msg(res)
        topics = []
        if decode_data['type'] == '_sys_msgs::Result':
            data = decode_data['data'].split(';')
            for t in data:
                url_type = t.split(',')
                topics.append(url_type)
            if len(topics) > 0 and len(topics[0]) == 3:
                max_widths1 = [max(len(str(d[i])) for d in topics) for i in range(len(columns))]
                max_widths2 = [len(d) for d in columns]
                max_widths = [max(w1, w2) for w1, w2 in zip(max_widths1, max_widths2)]
            else:
                max_widths = [len(d) for d in columns]
                topics = []
            for i, column in enumerate(columns):
                print(f'| {column:>{max_widths[i]}} ', end='')
            print('|')
            for row in topics:
                for i, value in enumerate(row):
                    print(f'| {value:>{max_widths[i]}} ', end='')
                print('|')
            return True
        return False

    last_data = b''
    big_msg = 0
    while True:
        try:
            data = client_socket.recv(4096)
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
                _quit = False
                for msg in recv_msgs:
                    if _parse_msg(msg):
                        _quit = True
                        break
                if _quit:
                    break

        except Exception as e:
            print(e)
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'cmd',
        nargs='+',
        help='Your Command (list, hz, echo)')
    parser.add_argument(
        '--ip',
        type=str,
        default='127.0.0.1',
        help='SpireMS Core IP')
    parser.add_argument(
        '--port',
        type=int,
        default=9094,
        help='SpireMS Core Port')
    args = parser.parse_args()
    # print(args.ip)
    # print(args.port)
    # print(args.cmd)
    if args.cmd[0] in ['list', 'hz', 'echo']:
        if 'list' == args.cmd[0]:
            _list(args.ip, args.port)
        if 'echo' == args.cmd[0]:
            assert len(args.cmd) > 1, "Usage: sms echo [topic_url]"
            _echo(args.cmd[1], args.ip, args.port)
        if 'hz' == args.cmd[0]:
            assert len(args.cmd) > 1, "Usage: sms hz [topic_url]"
            _hz(args.cmd[1], args.ip, args.port)
    else:
        pass


if __name__ == '__main__':
    main()
