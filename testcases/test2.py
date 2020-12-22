# Copyright 2020 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""
######################## train alexnet example ########################
train alexnet and get network model files(.ckpt) :
python train.py --data_path /YourDataPath
"""

import ast
import argparse
import os
from src.config import alexnet_cifar10_cfg, alexnet_imagenet_cfg
from src.dataset import create_dataset_cifar10, create_dataset_imagenet
from src.generator_lr import get_lr_cifar10, get_lr_imagenet
from src.alexnet import AlexNet
from src.get_param_groups import get_param_groups
import mindspore.nn as nn
from mindspore.communication.management import init, get_rank
from mindspore import dataset as de
from mindspore import context
from mindspore import Tensor
from mindspore.train import Model
from mindspore.context import ParallelMode
from mindspore.nn.metrics import Accuracy
from mindspore.train.callback import ModelCheckpoint, CheckpointConfig, LossMonitor, TimeMonitor
from mindspore.common import set_seed

set_seed(1)
de.config.set_seed(1)

if __name__ == "__main__":
    parser = argparse.$hole$
