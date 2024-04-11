#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import numpy as np
import cv2
import os
from PIL import ImageFont, ImageDraw, Image
import csv


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
        show_h, show_w = 120, 899
        menu_img = img_show_[-show_h:, :show_w]
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
        img_show_[-show_h:, :show_w] = menu_img
        img = img_show_
    return img


g_track_left = None
g_track_bottom = None
g_track_height = None


def track_coordinate_convert(pts, left=None, bottom=None, height=None, margin_=100) -> np.ndarray:
    global g_track_left, g_track_bottom, g_track_height
    assert g_track_left is not None or left is not None
    assert g_track_bottom is not None or bottom is not None
    assert g_track_height is not None or height is not None
    if g_track_left is None:
        g_track_left = left
    if g_track_bottom is None:
        g_track_bottom = bottom
    if g_track_height is None:
        g_track_height = height
    pts[:, 0] += (0 - g_track_left) + margin_
    pts[:, 1] += (0 - g_track_bottom) + margin_
    pts[:, 1] = g_track_height - pts[:, 1]
    return pts


def track_boundary_parse():
    # traj_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../res/trajectories.csv')
    traj_right_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../res/yas_full_right.csv')
    traj_left_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../res/yas_full_left.csv')
    left_line = []
    right_line = []
    mid_line = []
    f_right = open(traj_right_path, 'r')
    f_left = open(traj_left_path, 'r')
    csv_list = csv.reader(f_right)
    for i, csv_row in enumerate(csv_list):
        if i > 0:
            right_line.append([csv_row[0], csv_row[1]])
    f_right.close()
    csv_list = csv.reader(f_left)
    for i, csv_row in enumerate(csv_list):
        if i > 0:
            left_line.append([csv_row[0], csv_row[1]])
    f_left.close()
    """
    with open(traj_path, 'r') as f:
        csv_list = csv.reader(f)
        for i, csv_row in enumerate(csv_list):
            if i > 0:
                # left_line.append([csv_row[0], csv_row[1]])  # x, y
                # right_line.append([csv_row[2], csv_row[3]])
                mid_line.append([csv_row[4], csv_row[5]])
    """
    left_line = np.array(left_line, dtype=np.float32)
    right_line = np.array(right_line, dtype=np.float32)
    # mid_line = np.array(mid_line, dtype=np.float32)
    line_left = left_line[:, 0].min()
    line_bottom = left_line[:, 1].min()
    line_right = left_line[:, 0].max()
    line_top = left_line[:, 1].max()
    margin = 100
    w, h = (line_right - line_left) + 2 * margin, (line_top - line_bottom) + 2 * margin

    # pts = track_coordinate_convert(mid_line, line_left, line_bottom, h, margin).astype(np.int32)
    left_line = track_coordinate_convert(left_line, line_left, line_bottom, h, margin).astype(np.int32)
    right_line = track_coordinate_convert(right_line).astype(np.int32)

    img = np.zeros((int(h), int(w), 3), np.uint8)
    # img_sml = np.zeros((int(h / 2), int(w / 2), 3), np.uint8)
    # img_big = np.zeros((int(h) * 2, int(w) * 2, 3), np.uint8)
    """
    for pt in pts:
        img = cv2.circle(img, pt, 4, (255, 255, 255), -1)
    for pt in left_line:
        img = cv2.circle(img, pt, 4, (255, 0, 0), -1)
    """
    # img = cv2.polylines(img, [pts], True, (255, 255, 255), 1)
    """
    left_line_big = np.array([[pt[0] * 2, pt[1] * 2] for pt in left_line], dtype=np.int32)
    right_line_big = np.array([[pt[0] * 2, pt[1] * 2] for pt in right_line], dtype=np.int32)
    mg_big = cv2.polylines(img_big, [left_line_big], True, (255, 255, 255), 1, cv2.LINE_AA)
    img_big = cv2.polylines(img_big, [right_line_big], True, (255, 255, 255), 1, cv2.LINE_AA)

    left_line_sml = np.array([[pt[0] / 2, pt[1] / 2] for pt in left_line], dtype=np.int32)
    right_line_sml = np.array([[pt[0] / 2, pt[1] / 2] for pt in right_line], dtype=np.int32)
    img_sml = cv2.polylines(img_sml, [left_line_sml], True, (255, 255, 255), 1, cv2.LINE_AA)
    img_sml = cv2.polylines(img_sml, [right_line_sml], True, (255, 255, 255), 1, cv2.LINE_AA)
    """
    img = cv2.polylines(img, [left_line], True, (255, 255, 255), 1, cv2.LINE_AA)
    img = cv2.polylines(img, [right_line], True, (255, 255, 255), 1, cv2.LINE_AA)

    # img = cv2.resize(img, (int(img.shape[1] / 3), int(img.shape[0] / 3)))
    # cv2.imwrite('C:/deep/track.png', img)
    # cv2.imshow("img", img)
    return left_line, right_line, (int(w), int(h))


def draw_track_map(
    img: np.ndarray,
    left_line: np.ndarray,
    right_line: np.ndarray,
    map_size: tuple,
    localization: tuple,
    orientation_z: float,
    velocity: float,
    acceleration: float,
    local: bool = False
):
    if len(img.shape) == 3 and img.shape[0] == 720 and img.shape[1] == 1280:
        img_show_ = img.copy()
        # 316, 600
        draw_map_h = 720
        draw_map_w = 380
        if local:
            full_map_h = draw_map_h * 8
            full_map_w = draw_map_w * 8
            scale_x = full_map_w / map_size[0]
            scale_y = full_map_h / map_size[1]
            map_mask = np.zeros((full_map_h, full_map_w, 3), dtype=np.uint8)

            left_line_sml = np.array([[pt[0] * scale_x, pt[1] * scale_y] for pt in left_line], dtype=np.int32)
            right_line_sml = np.array([[pt[0] * scale_x, pt[1] * scale_y] for pt in right_line], dtype=np.int32)
            map_mask = cv2.polylines(map_mask, [left_line_sml], True, (255, 255, 255), 1, cv2.LINE_AA)
            map_mask = cv2.polylines(map_mask, [right_line_sml], True, (255, 255, 255), 1, cv2.LINE_AA)
            loc = np.array([localization]).astype(np.float64)
            loc = track_coordinate_convert(loc)
            loc = np.array([[pt[0] * scale_x, pt[1] * scale_y] for pt in loc], dtype=np.int32)
            pt = loc[0]
            map_mask = cv2.circle(map_mask, pt, 4, (0, 0, 255), -1)

            pil_image = Image.fromarray(cv2.cvtColor(map_mask, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil_image)
            draw.text((pt[0], pt[1] - 30), "{:.2f} m/s".format(velocity), font=font, fill=font_color)
            draw.text((pt[0], pt[1] - 50), "{:.2f} m/s^2".format(acceleration), font=font, fill=font_color)
            map_mask = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

            # [10, 0]
            r = 20
            arrow_x = int(np.cos(orientation_z) * r)
            arrow_y = int(np.sin(-orientation_z) * r)
            map_mask = cv2.line(map_mask, pt, (pt[0] + arrow_x, pt[1] + arrow_y), (0, 255, 255), 1, cv2.LINE_AA)
            x1 = pt[0] - draw_map_w / 2
            x2 = pt[0] + draw_map_w / 2
            y1 = pt[1] - draw_map_h / 2
            y2 = pt[1] + draw_map_h / 2
            if x1 < 0:
                x1 = 0
                x2 = draw_map_w
            if y1 < 0:
                y1 = 0
                y2 = draw_map_h
            if x2 > full_map_w:
                x2 = full_map_w
                x1 = full_map_w - draw_map_w
            if y2 > full_map_h:
                y2 = full_map_h
                y1 = full_map_h - draw_map_h
            map_mask = map_mask[int(y1): int(y2), int(x1): int(x2)]
            img_map = img_show_[:draw_map_h, -draw_map_w:]
            # print(map_mask.shape)
            # print(img_map.shape)
            img_map = cv2.addWeighted(img_map, 0.5, map_mask, 0.5, 0)
            img_show_[:draw_map_h, -draw_map_w:] = img_map
            img = img_show_
        else:
            scale_x = draw_map_w / map_size[0]
            scale_y = draw_map_h / map_size[1]

            img_map = img_show_[:draw_map_h, -draw_map_w:]
            map_mask = np.zeros_like(img_map, dtype=np.uint8)
            img_map = cv2.addWeighted(img_map, 0.5, map_mask, 0.5, 0)

            left_line_sml = np.array([[pt[0] * scale_x, pt[1] * scale_y] for pt in left_line], dtype=np.int32)
            right_line_sml = np.array([[pt[0] * scale_x, pt[1] * scale_y] for pt in right_line], dtype=np.int32)
            img_map = cv2.polylines(img_map, [left_line_sml], True, (255, 255, 255), 1, cv2.LINE_AA)
            img_map = cv2.polylines(img_map, [right_line_sml], True, (255, 255, 255), 1, cv2.LINE_AA)

            loc = np.array([localization]).astype(np.float64)
            loc = track_coordinate_convert(loc)
            loc = np.array([[pt[0] * scale_x, pt[1] * scale_y] for pt in loc], dtype=np.int32)
            for pt in loc:
                img_map = cv2.circle(img_map, pt, 4, (0, 0, 255), -1)
            img_show_[:draw_map_h, -draw_map_w:] = img_map
            img = img_show_
    return img


if __name__ == '__main__':
    _left_line, _right_line, (_w, _h) = track_boundary_parse()
    print(_left_line.shape)
    print(_right_line.shape)
    print(_w, _h)
    draw_track_map(np.zeros((720, 1280, 3), dtype=np.uint8), _left_line, _right_line, (_w, _h), (0, 0))
