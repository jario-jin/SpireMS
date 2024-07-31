#!/usr/bin/env python3
# -*- coding:utf-8 -*-
# @Author: renjin@bit.edu.cn
# @Date  : 2024-07-08

from spirems import Publisher, def_msg
import time
import random
from datetime import datetime


pub = Publisher(
    '/talker/hello_spirems',
    'std_msgs::String'
)


while True:
    time.sleep(1)
    tpc = def_msg('std_msgs::String')
    tpc['data'] = '[{}] Hello World'.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    pub.publish(tpc)
