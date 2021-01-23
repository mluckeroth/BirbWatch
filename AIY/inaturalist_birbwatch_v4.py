#!/usr/bin/env python3
#
# Copyright 2017 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Camera image classification demo code.
Runs continuous image classification on camera frames and prints detected object
classes.
MODIFIED: Nov 29, 2020 Mark Luckeroth
run inaturalist model from Pi Camera and log filtered data
"""
import os
import argparse
import contextlib
import logging
import utilities
import collections
import itertools
import datetime
import random
from astral.sun import sun
from astral import LocationInfo

from aiy.vision.inference import CameraInference
from aiy.vision.models import inaturalist_classification
from picamera import PiCamera

log_path = '../logs/'
max_log = 10000000 #bytes in directory
log = utilities.configure_logger('default', log_path+ts()+'_birbdata.log')


def ts():
    return datetime.datetime.now().strftime("%Y-%b-%d_%H:%M")


def flip(p):
    return random.random() < p


def get_size(start_path = '.'):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def sun_up():
    """is the sun up this hour? (assumes location is Portland, OR, USA)"""
    city = LocationInfo("Portland", "OR, USA", "US/Pacific", 45.5051, 122.6750)
    s = sun(city.observer, date=(datetime.datetime.today() + datetime.timedelta(days=1)), tzinfo=city.timezone)
    local_sunrise = (s['sunrise'] - datetime.timedelta(hours=8)).replace(tzinfo=None)
    local_sunset = (s['sunset'] - datetime.timedelta(hours=8)).replace(tzinfo=None)
    time_to_sundown = local_sunset - datetime.datetime.now()
    time_since_sunup = datetime.datetime.now() - local_sunrise
    overlap = datetime.timedelta(hours=-0.5)
    return (time_since_sunup > overlap) & (time_to_sundown > overlap)


def classes_info(classes):
    return ', '.join('%s (%.2f)' % pair for pair in classes)

@contextlib.contextmanager
def CameraPreview(camera, enabled):
    if enabled:
        camera.start_preview()
    try:
        yield
    finally:
        if enabled:
            camera.stop_preview()

def main():
    parser = argparse.ArgumentParser('Image classification camera inference example.')
    parser.add_argument('--num_frames', '-n', type=int, default=None,
        help='Sets the number of frames to run for, otherwise runs forever.')
    parser.add_argument('--num_objects', '-c', type=int, default=3,
        help='Sets the number of object interences to print.')
    parser.add_argument('--nopreview', dest='preview', action='store_false', default=True,
        help='Enable camera preview')
    parser.add_argument('--threshold', '-t', type=float, default=0.1,
                        help='Classification probability threshold.')
    parser.add_argument('--top_k', '-k', type=int, default=3,
                        help='Max number of returned classes.')
    parser.add_argument('--sparse', '-s', action='store_true', default=False,
                        help='Use sparse tensors')
    parser.add_argument('--model', '-m', choices=('plants', 'insects', 'birds'), required=True,
                        help='Model to run')
    args = parser.parse_args()

    model_type = {'plants':  inaturalist_classification.PLANTS,
                  'insects': inaturalist_classification.INSECTS,
                  'birds':   inaturalist_classification.BIRDS}[args.model]

    collector = collections.deque([], maxlen=7)
    with PiCamera(sensor_mode=4, framerate=10) as camera, \
         CameraPreview(camera, enabled=args.preview), \
         CameraInference(inaturalist_classification.model(model_type)) as inference:
        for result in inference.run(args.num_frames):
            classes = inaturalist_classification.get_classes(result, top_k=args.top_k, threshold=args.threshold)
            if classes:
                collector.appendleft(list(itertools.chain(*classes))[0])
            if len(collector) > 5:
                if collector[0] != 'background' and collector.count(collector[0]) > 4:
                    log.info(classes_info(classes))
                    collector.clear()
                    if get_size(log_path) < max_log and flip(0.1):
                        camera.capture(log_path+ts()+'.jpg')
            if classes:
                camera.annotate_text = '%s (%.2f)' % classes[0]

if __name__ == '__main__':
    if sun_up():
        main()
    else:
        print("Birbs are still sleeping")