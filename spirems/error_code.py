#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from msg_helper import get_all_msg_types


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
    209: "Cannot register as both a publisher and a subscriber"
}


def ec2msg(ec: int) -> dict:
    msg = get_all_msg_types()['_sys_msgs::Result'].copy()
    msg['error_code'] = ec
    msg['data'] = ERROR_CODE_BOOK[ec]
    return msg
