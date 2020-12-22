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
"""train Xception."""
import os
import time
import argparse
import numpy as np

from mindspore import context
from mindspore import Tensor
from mindspore.nn.optim.momentum import Momentum
from mindspore.train.model import Model, ParallelMode
from mindspore.train.callback import ModelCheckpoint, CheckpointConfig, Callback
from mindspore.train.serialization import load_checkpoint, load_param_into_net
from mindspore.communication.management import init, get_rank, get_group_size
from mindspore.train.loss_scale_manager import FixedLossScaleManager
from mindspore.common import dtype as mstype
from mindspore.common import set_seed

from src.lr_generator import get_lr
from src.Xception import xception
from src.config import config
from src.dataset import create_dataset
from src.loss import CrossEntropySmooth

set_seed(1)

class Monitor(Callback):
    """
    Monitor loss and time.

    Args:
        lr_init (numpy array): train lr

    Returns:
        None

    Examples:
        >>> Monitor(lr_init=Tensor([0.05]*100).asnumpy())
    """

    def __init__(self, lr_init=None):
        super(Monitor, self).__init__()
        self.lr_init = lr_init
        self.lr_init_len = len(lr_init)

    def epoch_begin(self, run_context):
        self.losses = []
        self.epoch_time = time.time()

    def epoch_end(self, run_context):
        cb_params = run_context.original_args()

        epoch_mseconds = (time.time() - self.epoch_time) * 1000
        per_step_mseconds = epoch_mseconds / cb_params.batch_num
        print("epoch time: {:5.3f}, per step time: {:5.3f}, avg loss: {:5.3f}".format(epoch_mseconds,
                                                                                      per_step_mseconds,
                                                                                      np.mean(self.losses)))

    def step_begin(self, run_context):
        self.step_time = time.time()

    def step_end(self, run_context):
        cb_params = run_context.original_args()
        step_mseconds = (time.time() - self.step_time) * 1000
        step_loss = cb_params.net_outputs

        if isinstance(step_loss, (tuple, list)) and isinstance(step_loss[0], Tensor):
            step_loss = step_loss[0]
        if isinstance(step_loss, Tensor):
            step_loss = np.mean(step_loss.asnumpy())

        self.losses.append(step_loss)
        cur_step_in_epoch = (cb_params.cur_step_num - 1) % cb_params.batch_num

        print("epoch: [{:3d}/{:3d}], step:[{:5d}/{:5d}], loss:[{:5.3f}/{:5.3f}], time:[{:5.3f}], lr:[{:5.3f}]".format(
            cb_params.cur_epoch_num - 1 + config.finish_epoch, cb_params.epoch_num + config.finish_epoch,
            cur_step_in_epoch, cb_params.batch_num, step_loss,
            np.mean(self.losses), step_mseconds, self.lr_init[cb_params.cur_step_num - 1]))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='image classification training')
    parser.add_argument('--is_distributed', action='store_true', default=False, help='distributed training')
    parser.add_argument('--device_target', type=str, default='Ascend', help='run platform')
    parser.add_argument('--dataset_path', type=str, default=None, help='dataset path')
    parser.add_argument('--resume', type=str, default='', help='resume training with existed checkpoint')
    args_opt = parser.parse_args()

    if args_opt.device_target == "Ascend":
        #train on Ascend
        context.set_context(mode=context.GRAPH_MODE, device_target='Ascend', save_graphs=False)

        # init distributed
        if args_opt.is_distributed:
            if os.getenv('DEVICE_ID', "not_set").isdigit():
                context.set_context(device_id=int(os.getenv('DEVICE_ID')))
            init()
            rank = get_rank()
            group_size = get_group_size()
            parallel_mode = ParallelMode.DATA_PARALLEL
            context.set_auto_parallel_context(parallel_mode=parallel_mode, device_num=group_size, gradients_mean=True)
        else:
            rank = 0
            group_size = 1
            context.set_context(device_id=0)

        # define network
        net = xception(class_num=config.class_num)
        net.to_float(mstype.float16)

        # define loss
        if not config.use_label_smooth:
            config.label_smooth_factor = 0.0
        loss = CrossEntropySmooth(smooth_factor=config.label_smooth_factor, num_classes=config.class_num)

        # define dataset
        dataset = create_dataset(args_opt.dataset_path, do_train=True, batch_size=config.batch_size,
                                 device_num=group_size, rank=rank)
        step_size = dataset.get_dataset_size()

        # resume
        if args_opt.resume:
            ckpt = load_checkpoint(args_opt.resume)
            load_param_into_net(net, ckpt)

        # get learning rate
        loss_scale = FixedLossScaleManager(config.loss_scale, drop_overflow_update=False)
        lr = Tensor(get_lr(lr_init=config.lr_init,
                           lr_end=config.lr_end,
                           lr_max=config.lr_max,
                           warmup_epochs=config.warmup_epochs,
                           total_epochs=config.epoch_size,
                           steps_per_epoch=step_size,
                           lr_decay_mode=config.lr_decay_mode))

        # define optimization
        opt = Momentum(net.trainable_params(), lr, config.momentum, config.weight_decay, config.loss_scale)

        # define model
        model = Model(net, loss_fn=loss, optimizer=opt, loss_scale_manager=loss_scale, metrics={'acc'},
                      amp_level='O3', keep_batchnorm_fp32=True)

        # define callbacks
        cb = [Monitor(lr_init=lr.asnumpy())]
        if config.save_checkpoint:
            save_ckpt_path = os.path.join(config.save_checkpoint_path, 'model_' + str(rank) + '/')
            config_ck = CheckpointConfig(save_checkpoint_steps=config.save_checkpoint_epochs * step_size,
                                         keep_checkpoint_max=config.keep_checkpoint_max)
            ckpt_cb = ModelCheckpoint(f"Xception-rank{rank}", directory=save_ckpt_path, config=config_ck)

        # begin train
        if args_opt.is_distributed:
            if rank == 0:
                cb += [ckpt_cb]
            model.train(config.epoch_size - config.finish_epoch, dataset, callbacks=cb, dataset_sink_mode=False)
        else:
            cb += [ckpt_cb]
            model.train(config.epoch_size - config.finish_epoch, dataset, callbacks=cb, dataset_sink_mode=False)
        print("train success")
    else:
        raise ValueError("Unsupported device_target.")
