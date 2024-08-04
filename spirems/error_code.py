#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

from spirems.msg_helper import get_all_msg_types, def_msg


ERROR_CODE_BOOK = {
    101: "Topic parsing error",
    201: "topic_url wrong: at least 2 chars",
    202: "topic_url wrong: need started with '/'",
    203: "topic_url wrong: only to use 'a-z', '0-9', '_' or '/'",
    204: "topic_url wrong: as the same as the existing",
    205: "topic_type wrong: Unsupported topic type",
    206: "Publisher/Subscriber does not include the topic_type and url fields",
    207: "Uploaded unregistered topic",
    208: "The topic type uploaded does not match the registered topic type",
    209: "Cannot register as both a publisher and a subscriber",
    210: "node_name wrong: at least 2 chars",
    211: "node_name wrong: only to use 'a-z', '0-9' or '_'",
    212: "Parameter does not include the node_name field",
    213: "Cannot register Parameter with a publisher or a subscriber",
    214: "node_name wrong: already exists",
    215: "The current parameter node is not registered",
    216: "node_name wrong: cannot start with '_'",
    217: "param_key wrong: at least 2 chars",
    218: "param_key wrong: only to use 'a-z', '0-9' or '_', except for the first '/'",
    219: "param_key wrong: cannot start with '_'",
    220: "global_param_key wrong: at least 6 chars",
    221: "global_param_key wrong: only to use 'a-z', '0-9', '_' or '/'",
    222: "global_param_key wrong: should start with '/'",
    223: "_global param node cannot create new parameters, only update parameters"
}


def ec2msg(ec: int) -> dict:
    msg = def_msg('_sys_msgs::Result')
    msg['error_code'] = ec
    msg['data'] = ERROR_CODE_BOOK[ec]
    return msg


def ec2str(ec: int) -> str:
    return ERROR_CODE_BOOK[ec]
