#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import re
import setuptools
import glob
import os


with open("spirems/__init__.py", "r") as f:
    version = re.search(
        r'^__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
        f.read(), re.MULTILINE
    ).group(1)


with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()


def get_package_data():
    data = []
    data.append('msgs/_sys_msgs/*.json')
    data.append('msgs/_visual_msgs/*.json')
    data.append('json_msgs/geometry_msgs/*.json')
    data.append('json_msgs/sensor_msgs/*.json')
    data.append('json_msgs/spirecv_msgs/*.json')
    data.append('json_msgs/std_msgs/*.json')
    data.append('json_schemas/geometry_msgs/*.json')
    data.append('json_schemas/sensor_msgs/*.json')
    data.append('json_schemas/std_msgs/*.json')
    data.append('logs/*.md')
    data.append('res/*.ttf')
    data.append('res/*.jpg')
    data.append('res/*.csv')
    data.append('res/*.json')
    return {'spirems': data}


setuptools.setup(
    name="spirems",
    version=version,
    author="jin&team",
    author_email="renjin@bit.edu.cn",
    python_requires=">=3.8",
    long_description=long_description,
    long_description_content_type='text/markdown',
    classifiers=["Programming Language :: Python :: 3", "Operating System :: OS Independent"],
    package_dir={'spirems': 'spirems'},
    package_data=get_package_data(),
    packages=setuptools.find_packages(),
    entry_points = {
        'console_scripts': [
            'sms=spirems.sms:main',
            'smscore=spirems.core:main',
            'smsparam=spirems.smsparam:main'
        ],
    },
    install_requires=("numpy", "opencv-python", "psutil", "jsonschema"),
)
