#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import socket
import time

from spirems.msg_helper import (encode_msg, decode_msg, get_all_msg_types, check_msg,
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

    client_socket.send(encode_msg(get_all_msg_types()['_sys_msgs::SmsTopicList']))
    columns = ['Topics', 'Type']

    def _parse_msg(res):
        success, decode_data = decode_msg(res)
        topics = []
        if decode_data['type'] == '_sys_msgs::Result':
            data = decode_data['data'].split(';')
            for t in data:
                url_type = t.split(',')
                topics.append(url_type)
            if len(topics) > 0 and len(topics[0]) == 2:
                max_widths = [max(len(str(d[i])) for d in topics) for i in range(len(columns))]
            else:
                max_widths = [max(len(str(d[i])) for d in columns) for i in range(len(columns))]
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
                _quit = False
                for msg in checked_msgs:
                    if _parse_msg(msg):
                        _quit = True
                        break
                if _quit:
                    break

        except Exception as e:
            print(e)
            break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'cmd',
        nargs='+',
        help='Your Command (list, hz, echo)')
    parser.add_argument(
        '--ip',
        type=str,
        default='127.0.0.1',
        help='SpireMS Server IP')
    parser.add_argument(
        '--port',
        type=int,
        default=9094,
        help='SpireMS Server Port')
    args = parser.parse_args()
    # print(args.ip)
    # print(args.port)
    # print(args.cmd)
    if args.cmd[0] in ['list', 'hz', 'echo']:
        if 'list' == args.cmd[0]:
            _list(args.ip, args.port)
        if 'echo' == args.cmd[0]:
            assert len(args.cmd) > 1, "You should subscribe a topic in Command"
            _echo(args.cmd[1], args.ip, args.port)
        if 'hz' == args.cmd[0]:
            assert len(args.cmd) > 1, "You should subscribe a topic in Command"
            _hz(args.cmd[1], args.ip, args.port)
    else:
        pass
