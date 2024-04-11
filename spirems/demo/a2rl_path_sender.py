#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import json
import os
import time
from spirems import Publisher, get_all_msg_types


pub = Publisher('/a2rl/ego_loc', 'std_msgs::NumberMultiArray', ip='127.0.0.1')
yas_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../res/optm_path.json')
with open(yas_path, 'r') as file:
    path_dict = json.load(file)
    line = path_dict['ReferenceLine']
    speed = path_dict['ReferenceSpeed']
    while 1:
        for pt, speed_pt in zip(line, speed):
            time.sleep(0.05)
            tpc = get_all_msg_types()['std_msgs::NumberMultiArray'].copy()
            tpc['data'] = [pt[0], pt[1], 0, speed_pt, speed_pt, 0, 0]
            pub.publish(tpc)
