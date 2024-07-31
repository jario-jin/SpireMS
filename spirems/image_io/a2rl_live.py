#!/usr/bin/env python3
# -*- coding:utf-8 -*-
from spirems.subscriber import Subscriber
from spirems.publisher import Publisher
from spirems.image_io.adaptor import sms2cvimg
from spirems import def_msg
from spirems.image_io.visual_helper import draw_charts, load_a2rl_logo, track_boundary_parse, draw_track_map
import cv2
import numpy as np


img2 = np.ones((720, 1280, 3), dtype=np.uint8) * 200
img2_on = False
img2_ready = False


def callback_f(msg):
    global img2, img2_ready
    img2_ready = False
    img2 = sms2cvimg(msg)
    img2_ready = True


a2rl_visual = def_msg('_visual_msgs::A2RLMonit')


def callback_monit(msg):
    global a2rl_visual
    cpu_usage = float(msg['data'][0])
    mem_left = a2rl_visual["bar_chart_items"][1]['val_max'] - float(msg['data'][1])
    disk_left = a2rl_visual["bar_chart_items"][2]['val_max'] - float(msg['data'][4]) / 1024
    cpu_temp = float(msg['data'][7])
    a2rl_visual["bar_chart_items"][0]['val'] = cpu_usage
    a2rl_visual["bar_chart_items"][1]['val'] = mem_left
    a2rl_visual["bar_chart_items"][2]['val'] = disk_left
    a2rl_visual["bar_chart_items"][3]['val'] = cpu_temp


position_x = -122.2
position_y = -627.5
position_z = 0
orientation_z = 0
velocity = 0
acceleration = 0
lateral_error = 0
code19_x = -50000
code19_y = -50000
code19_v = 0
code19_yaw = 0


def callback_ego_loc(msg):
    global position_x, position_y, position_z, orientation_z, velocity, acceleration, lateral_error, \
        code19_x, code19_y, code19_v, code19_yaw
    position_x = msg['data'][0]
    # print(position_x)
    position_y = msg['data'][1]
    # print(position_y)
    # position_z = msg['data'][2]
    orientation_z = msg['data'][2]
    velocity_x = msg['data'][3]
    # print(velocity_x)
    velocity_y = msg['data'][4]
    velocity = np.sqrt(velocity_x ** 2 + velocity_y ** 2)
    acceleration_x = msg['data'][5]
    acceleration_y = msg['data'][6]
    acceleration = np.sqrt(acceleration_x ** 2 + acceleration_y ** 2)
    ice_water_temp = msg['data'][7]
    ice_oil_temp = msg['data'][8]
    ice_engine_speed = msg['data'][9]
    lateral_error = msg['data'][10]
    code19_x = msg['data'][11]
    code19_y = msg['data'][12]
    code19_v = msg['data'][13]
    code19_yaw = msg['data'][14]
    a2rl_visual["bar_chart_items"][4]['val'] = ice_water_temp
    print(msg['data'])
    a2rl_visual["bar_chart_items"][5]['val'] = ice_oil_temp
    a2rl_visual["bar_chart_items"][6]['val'] = int(ice_engine_speed)
    a2rl_visual["bar_chart_items"][7]['val'] = lateral_error


if __name__ == '__main__':
    sub = Subscriber('/sensors/camera/image_raw', 'sensor_msgs::CompressedImage', callback_f,
                     ip='47.91.115.171')  # 47.91.115.171
    pub = Publisher('/signal/live_switch', 'std_msgs::Number',
                    ip='47.91.115.171')
    sub2 = Subscriber('/a2rl/monit', 'std_msgs::NumberMultiArray', callback_monit,
                      ip='47.91.115.171')  # 47.91.115.171
    sub3 = Subscriber('/a2rl/ego_loc', 'std_msgs::NumberMultiArray', callback_ego_loc,
                      ip='47.91.115.171')  # 47.91.115.171
    num_tpc = def_msg('std_msgs::Number')
    left_line, right_line, (map_w, map_h) = track_boundary_parse()
    running = True
    default_img = load_a2rl_logo()
    default_img = cv2.resize(default_img, (1280, 720))
    img = default_img
    use_local = False
    # cv2.namedWindow('img', cv2.WINDOW_NORMAL)
    # cv2.setWindowProperty('img', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    while running:
        if img2_on and img2_ready and img2 is not None:
            img = img2.copy()
            img = cv2.resize(img, (1280, 720))
        img_show = draw_charts(img, a2rl_visual)
        img_show = draw_track_map(img_show, left_line, right_line, (map_w, map_h),
                                  (position_x, position_y), orientation_z, velocity, acceleration,
                                  (code19_x, code19_y, code19_v, code19_yaw))

        cv2.imshow('img', img_show)
        c = cv2.waitKey(5)
        if c > 0:
            if c == 48:    # 0
                print('press key: {}'.format(0))
                img2_on = False
                img = default_img
                sub.suspend()
            elif c == 49:  # 1
                print('press key: {}'.format(1))
                num_tpc['data'] = 1
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
            elif c == 50:  # 2
                print('press key: {}'.format(2))
                num_tpc['data'] = 2
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
            elif c == 51:  # 3
                print('press key: {}'.format(3))
                num_tpc['data'] = 3
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
            elif c == 52:  # 4
                print('press key: {}'.format(4))
                num_tpc['data'] = 4
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
            elif c == 53:  # 5
                print('press key: {}'.format(5))
                num_tpc['data'] = 5
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
            elif c == 54:  # 6
                print('press key: {}'.format(6))
                num_tpc['data'] = 6
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
            elif c == 55:  # 7
                """
                print('press key: {}'.format(7))
                num_tpc['data'] = 7
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
                """
                use_local = not use_local
            else:
                print(c)
