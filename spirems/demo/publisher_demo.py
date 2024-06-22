#!/usr/bin/env python3
# -*- coding:utf-8 -*-

from spirems import Publisher, get_all_msg_types
import time
import random
from datetime import datetime


pub = Publisher(
    '/talker/hello_spirems',
    'std_msgs::String',
    # ip='47.91.115.171'
)


while True:
    time.sleep(1)
    tpc = get_all_msg_types()['std_msgs::String'].copy()
    tpc['data'] = '[{}] Hello World'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    pub.publish(tpc)
