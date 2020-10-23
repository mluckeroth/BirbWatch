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

MODIFIED: Feb 17, 2019, Mark Luckeroth
run inaturalist model from Pi Camera
"""
import argparse
import contextlib

from aiy.vision.inference import CameraInference
from aiy.vision.models import inaturalist_classification
from picamera import PiCamera

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
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('--num_frames', '-n', type=int, default=None,
                        help='Sets the number of frames to run for, otherwise runs forever.')
    parser.add_argument('--threshold', '-t', type=float, default=0.1,
                        help='Classification probability threshold.')
    parser.add_argument('--top_k', '-k', type=int, default=5,
                        help='Max number of returned classes.')
    parser.add_argument('--sparse', '-s', action='store_true', default=False,
                        help='Use sparse tensors.')
    parser.add_argument('--model', '-m', choices=('plants', 'insects', 'birds'), required=True,
                        help='Model to run.')
    parser.add_argument('--nopreview', dest='preview', action='store_false', default=True,
                        help='Enable camera preview')
    args = parser.parse_args()

    model_type = {'plants':  inaturalist_classification.PLANTS,
                  'insects': inaturalist_classification.INSECTS,
                  'birds': inaturalist_classification.BIRDS}[args.model]

    with PiCamera(sensor_mode=4, framerate=10) as camera, \
         CameraPreview(camera, enabled=args.preview), \
         CameraInference(inaturalist_classification.model(model_type)) as inference:

         if args.sparse:
            configs = inaturalist_classification.sparse_configs(top_k=args.top_k,
                                                                threshold=args.threshold,
                                                                model_type=model_type)
            for result in inference.run(args.num_frames, sparse_configs=configs):
                classes = inaturalist_classification.get_classes_sparse(result)
                for i, (label, score) in enumerate(classes):
                    print('Result %d: %s (prob=%f)' % (i, label, score))
                if classes:
                    camera.annotate_text = '%s (%.2f)' % classes[0]

         else:
            for result in inference.run(args.num_frames):
                classes = inaturalist_classification.get_classes(result,
                                                                top_k=args.top_k,
                                                                threshold=args.threshold)
                for i, (label, score) in enumerate(classes):
                    print('Result %d: %s (prob=%f)' % (i, label, score))
                if classes:
                    camera.annotate_text = '%s (%.2f)' % classes[0]


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Interrupted')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)