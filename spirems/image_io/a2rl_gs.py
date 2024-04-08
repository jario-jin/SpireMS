#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import numpy as np

from spirems.subscriber import Subscriber
from spirems.publisher import Publisher
from spirems.image_io.adaptor import sms2cvimg
from spirems.image_io.visual_helper import load_a2rl_logo
from spirems import get_all_msg_types
import time
import cv2
from PIL import ImageFont, ImageDraw, Image


img2 = np.ones((720, 1280, 3), dtype=np.uint8) * 200
cpu_usage = 0
mem_free = 128
cpu_temp = 0
img2_on = False
img2_ready = False
net_send = 0
net_recv = 0
disk_free = 0
disk_read = 0
disk_write = 0

last_net_out = 0
last_net_in = 0
last_disk_read = 0
last_disk_write = 0
last_time = 0


font_path = '../res/fradmcn.ttf'
font_size = 17
font_color = (255, 255, 255)
font = ImageFont.truetype(font_path, font_size)


def pil_put_text(image: np.ndarray, text_position: tuple[float, float], text: str) -> np.ndarray:
    pil_image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(pil_image)
    draw.text(text_position, text, font=font, fill=font_color)
    image_with_text = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
    return image_with_text


def callback_monit(msg):
    global cpu_usage, mem_free, cpu_temp, net_send, net_recv, disk_free, disk_read, disk_write
    global last_net_out, last_net_in, last_disk_read, last_disk_write, last_time
    cpu_usage = float(msg['data'][0])
    mem_free = float(msg['data'][1])

    if last_net_out > 0:
        net_send = (msg['data'][2] - last_net_out) / (msg['timestamp'] - last_time)
    last_net_out = msg['data'][2]
    if last_net_in > 0:
        net_recv = (msg['data'][3] - last_net_in) / (msg['timestamp'] - last_time)
    last_net_in = msg['data'][3]

    disk_free = float(msg['data'][4])

    if last_disk_read > 0:
        disk_read = (msg['data'][5] - last_disk_read) / (msg['timestamp'] - last_time)
    last_disk_read = msg['data'][5]
    if last_disk_write > 0:
        disk_write = (msg['data'][6] - last_disk_write) / (msg['timestamp'] - last_time)
    last_disk_write = msg['data'][6]

    cpu_temp = float(msg['data'][7])
    # print(cpu_usage, mem_free)

    last_time = msg['timestamp']


def callback_f(msg):
    global img2, img2_ready
    img2_ready = False
    # print(time.time() - msg['timestamp'])
    img2 = sms2cvimg(msg)
    # cv2.imshow('img22', img2)
    img2_ready = True
    # cv2.waitKey(5)


def draw_menu_bar(menu_img: np.ndarray, posx: int, name: str, text: str, val: float, val_max: float) -> np.ndarray:
    x, y, w, h = (30+posx, 30, 10, 60)
    cv2.rectangle(menu_img, (x, y), (x + w, y + h), (255, 255, 255), 1)
    x, y, w, h = (30+posx, int(30 + 60 * (val_max - val) / val_max), 10, int(60 * val / val_max))
    cv2.rectangle(menu_img, (x, y), (x + w, y + h), (255, 255, 255), -1)

    menu_img = pil_put_text(menu_img, (20+posx, 8), text)
    menu_img = pil_put_text(menu_img, (20+posx, 94), name)
    # cv2.putText(menu_img, text, (20+posx, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
    # cv2.putText(menu_img, name, (20+posx, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    return menu_img


def load_menu(cv_img: np.ndarray) -> np.ndarray:
    img_show_ = cv_img.copy()
    menu_img = img_show_[600:, :]
    menu_mask = np.zeros_like(menu_img, dtype=np.uint8)
    menu_img = cv2.addWeighted(menu_img, 0.5, menu_mask, 0.5, 0)
    global cpu_usage, mem_free, cpu_temp, net_send, net_recv, disk_free, disk_read, disk_write
    menu_img = draw_menu_bar(menu_img, 0, "CPU", "{:.1f} %".format(cpu_usage), cpu_usage, 100)
    menu_img = draw_menu_bar(menu_img, 80, "Mem", "{:.1f} G".format(128 - mem_free), 128 - mem_free, 128)
    menu_img = draw_menu_bar(menu_img, 160, "Temp", "{:.1f}`C".format(cpu_temp), cpu_temp, 100)
    menu_img = draw_menu_bar(menu_img, 240, "N-S", "{:.2f}Mb/s".format(
        net_send * 1024), net_send * 1024, 100)
    menu_img = draw_menu_bar(menu_img, 320, "N-R", "{:.2f}Mb/s".format(
        net_recv * 1024), net_recv * 1024, 100)
    menu_img = draw_menu_bar(menu_img, 400, "Disk", "{:.1f}TB".format(
        15 - disk_free / 1024), 15 - disk_free / 1024, 15)
    menu_img = draw_menu_bar(menu_img, 480, "D-R", "{:.1f}Mb/s".format(
        disk_read * 1024), disk_read * 1024, 1000)
    menu_img = draw_menu_bar(menu_img, 560, "D-W", "{:.1f}Mb/s".format(
        disk_write * 1024), disk_write * 1024, 1000)
    img_show_[600:, :] = menu_img
    # cv2.imshow("menu_img", menu_img)
    # cv2.waitKey(5)
    return img_show_


if __name__ == '__main__':
    sub = Subscriber('/sensors/camera/image_raw', 'sensor_msgs::Image', callback_f,
                     ip='47.91.115.171')  # 47.91.115.171
    sub2 = Subscriber('/a2rl/monit', 'std_msgs::NumberMultiArray', callback_monit,
                      ip='47.91.115.171')  # 47.91.115.171
    pub = Publisher('/signal/live_switch', 'std_msgs::Number',
                    ip='47.91.115.171')
    num_tpc = get_all_msg_types()['std_msgs::Number'].copy()
    running = True
    default_img = load_a2rl_logo()
    default_img = cv2.resize(default_img, (1280, 720))
    img = default_img
    while running:
        if img2_on and img2_ready and img2 is not None:
            img = img2.copy()
            img = cv2.resize(img, (1280, 720))
        img_show = load_menu(img)
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
                print('press key: {}'.format(7))
                num_tpc['data'] = 7
                pub.publish(num_tpc)
                sub.unsuspend()
                img2_on = True
            else:
                print(c)
    sub.wait_key()
