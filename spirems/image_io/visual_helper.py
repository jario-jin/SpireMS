#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import numpy as np
import cv2
import os
from PIL import ImageFont, ImageDraw, Image


font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../res/fradmcn.ttf')
font_size = 17
font_color = (255, 255, 255)
font = ImageFont.truetype(font_path, font_size)


def load_a2rl_logo() -> np.ndarray:
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../res/racecar.jpg')
    default_img = cv2.imread(img_path)
    return default_img


def draw_charts(img: np.ndarray, visual_msg: dict) -> np.ndarray:
    if len(img.shape) == 3 and img.shape[0] == 720 and img.shape[1] == 1280:
        img_show_ = img.copy()
        menu_img = img_show_[600:, :]
        menu_mask = np.zeros_like(menu_img, dtype=np.uint8)
        menu_img = cv2.addWeighted(menu_img, 0.5, menu_mask, 0.5, 0)
        if 'bar_chart_items' in visual_msg:
            for item in visual_msg['bar_chart_items']:  # chart
                posx = item['posx']
                val = item['val']
                val_min = item['val_min']
                val_max = item['val_max']
                if val < val_min:
                    val = val_min
                if val > val_max:
                    val = val_max
                x, y, w, h = (30 + posx, 30, 10, 60)
                cv2.rectangle(menu_img, (x, y), (x + w, y + h), (255, 255, 255), 1)
                x, y, w, h = (30 + posx, int(30 + 60 * (val_max - val) / val_max), 10, int(60 * val / val_max))
                cv2.rectangle(menu_img, (x, y), (x + w, y + h), (255, 255, 255), -1)

            pil_image = Image.fromarray(cv2.cvtColor(menu_img, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)
            for item in visual_msg['bar_chart_items']:  # text
                posx = item['posx']
                text = item['title_refresh']
                name = item['title']
                val = item['val']
                val_min = item['val_min']
                val_max = item['val_max']
                if val < val_min:
                    val = val_min
                if val > val_max:
                    val = val_max
                draw.text((20 + posx, 8), text.format(val), font=font, fill=font_color)
                draw.text((20 + posx, 94), name, font=font, fill=font_color)
            menu_img = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)
        img_show_[600:, :] = menu_img
        img = img_show_
    return img
