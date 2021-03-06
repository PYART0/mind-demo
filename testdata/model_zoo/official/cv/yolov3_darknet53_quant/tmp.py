import os
import argparse
import datetime
import time
import sys
from collections import defaultdict

import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval

from mindspore import Tensor
from mindspore.context import ParallelMode
from mindspore import context
from mindspore.train.serialization import load_checkpoint, load_param_into_net
import mindspore as ms
from mindspore.compression.quant import QuantizationAwareTraining

from src.yolo import YOLOV3DarkNet53
from src.logger import get_logger
from src.yolo_dataset import create_yolo_dataset
from src.config import ConfigYOLOV3DarkNet53

devid = int(os.getenv('DEVICE_ID'))
context.set_context(mode=context.GRAPH_MODE, device_target="Ascend", save_graphs=True, device_id=devid)


class Redirct:
    def __init__(self):
        self.content = ""

    def write(self, content):
        self.content += content

    def flush(self):
        self.content = ""


class DetectionEngine:
    def __init__(self, args):
        self.ignore_threshold = args.ignore_threshold
        self.labels = ['person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
                       'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
                       'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
                       'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
                       'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
                       'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
                       'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake', 'chair',
                       'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop', 'mouse', 'remote',
                       'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book',
                       'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush']
        self.num_classes = len(self.labels)
        self.results = {}
        self.file_path = ''
        self.save_prefix = args.outputs_dir
        self.annFile = args.annFile
        self._coco = COCO(self.annFile)
        self._img_ids = list(sorted(self._coco.imgs.keys()))
        self.det_boxes = []
        self.nms_thresh = args.nms_thresh
        self.coco_catIds = self._coco.getCatIds()

    def do_nms_for_results(self):
        for img_id in self.results:
            for clsi in self.results[img_id]:
                dets = self.results[img_id][clsi]
                dets = np.array(dets)
                keep_index = self._nms(dets, self.nms_thresh)

                keep_box = [{'image_id': int(img_id),
                             'category_id': int(clsi),
                             'bbox': list(dets[i][:4].astype(float)),
                             'score': dets[i][4].astype(float)}
                            for i in keep_index]
                self.det_boxes.extend(keep_box)

    def _nms(self, dets, thresh):
        x1 = dets[:, 0]
        y1 = dets[:, 1]
        x2 = x1 + dets[:, 2]
        y2 = y1 + dets[:, 3]
        scores = dets[:, 4]

        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(ovr <= thresh)[0]
            order = order[inds + 1]
        return keep

    def write_result(self):
        import json
        t = datetime.datetime.now().strftime('_%Y_%m_%d_%H_%M_%S')
        try:
            self.file_path = self.save_prefix + '/predict' + t + '.json'
            f = open(self.file_path, 'w')
            json.dump(self.det_boxes, f)
        except IOError as e:
            raise RuntimeError("Unable to open json file to dump. What(): {}".format(str(e)))
        else:
            f.close()
            return self.file_path

    def get_eval_result(self):
        cocoGt = COCO(self.annFile)
        cocoDt = cocoGt.loadRes(self.file_path)
        cocoEval = COCOeval(cocoGt, cocoDt, 'bbox')
        cocoEval.evaluate()
        cocoEval.accumulate()
        rdct = Redirct()
        stdout = sys.stdout
        sys.stdout = rdct
        cocoEval.summarize()
        sys.stdout = stdout
        return rdct.content

    def detect(self, outputs, batch, image_shape, image_id):
        outputs_num = len(outputs)
        for batch_id in range(batch):
            for out_id in range(outputs_num):
                out_item = outputs[out_id]
                out_item_single = out_item[batch_id, :]
                dimensions = out_item_single.shape[:-1]
                out_num = 1
                for d in dimensions:
                    out_num *= d
                ori_w, ori_h = image_shape[batch_id]
                img_id = int(image_id[batch_id])
                x = out_item_single[..., 0] * ori_w
                y = out_item_single[..., 1] * ori_h
                w = out_item_single[..., 2] * ori_w
                h = out_item_single[..., 3] * ori_h

                conf = out_item_single[..., 4:5]
                cls_emb = out_item_single[..., 5:]

                cls_argmax = np.expand_dims(np.argmax(cls_emb, axis=-1), axis=-1)
                x = x.reshape(-1)
                y = y.reshape(-1)
                w = w.reshape(-1)
                h = h.reshape(-1)
                cls_emb = cls_emb.reshape(-1, 80)
                conf = conf.reshape(-1)
                cls_argmax = cls_argmax.reshape(-1)

                x_top_left = x - w / 2.
                y_top_left = y - h / 2.
                flag = np.random.random(cls_emb.shape) > sys.maxsize
                for i in range(flag.shape[0]):
                    c = cls_argmax[i]
                    flag[i, c] = True
                confidence = cls_emb[flag] * conf
                for x_lefti, y_lefti, wi, hi, confi, clsi in zip(x_top_left, y_top_left, w, h, confidence, cls_argmax):
                    if confi < self.ignore_threshold:
                        continue
                    if img_id not in self.results:
                        self.results[img_id] = defaultdict(list)
                    x_lefti = max(0, x_lefti)
                    y_lefti = max(0, y_lefti)
                    wi = min(wi, ori_w)
                    hi = min(hi, ori_h)
                    coco_clsi = self.coco_catIds[clsi]
                    self.results[img_id][coco_clsi].append([x_lefti, y_lefti, wi, hi, confi])


def parse_args():
    parser = argparse.ArgumentParser('mindspore coco testing')

    parser.add_argument('--data_dir', type=str, default="", help='Train data dir. Default: ""')
    parser.add_argument('--per_batch_size', default=1, type=int, help='Batch size for per device, Default: 1')

    parser.add_argument('--pretrained', default="", type=str,\
                       help='The model path, local pretrained model to load, Default: ""')

    parser.add_argument('--log_path', type=str, default="outputs/", help='Log save location, Default: "outputs/"')

    parser.add_argument('--nms_thresh', type=float, default=0.5, help='Threshold for NMS. Default: 0.5')
    parser.add_argument('--annFile', type=str, default="", help='The path to annotation. Default: ""')
    parser.add_argument('--testing_shape', type=str, default="", help='Shape for test. Default: ""')
    parser.add_argument('--ignore_threshold', type=float, default=0.001,\
                       help='Threshold to throw low quality boxes, Default: 0.001')

    args, _ = parser.parse_known_args()

    args.data_root = os.path.join(args.data_dir, 'val2014')
    args.annFile = os.path.join(args.data_dir, 'annotations/instances_val2014.json')

    return args


def conver_testing_shape(args):
    testing_shape = [int(args.testing_shape), int(args.testing_shape)]
    return testing_shape


def test():
    start_time = time.time()
    args = parse_args()

    args.outputs_dir = os.path.join(args.log_path,
                                    datetime.datetime.now().strftime('%Y-%m-%d_time_%H_%M_%S'))
    rank_id = int(os.environ.get('RANK_ID'))
    args.logger = get_logger(args.outputs_dir, rank_id)

    context.reset_auto_parallel_context()
    parallel_mode = ParallelMode.STAND_ALONE
    context.set_auto_parallel_context(parallel_mode=parallel_mode, gradients_mean=True, device_num=1)

    args.logger.info('Creating Network....')
    network = YOLOV3DarkNet53(is_training=False)

    config = ConfigYOLOV3DarkNet53()
    if args.testing_shape:
        config.test_img_shape = conver_testing_shape(args)

    if config.quantization_aware:
        quantizer = QuantizationAwareTraining(bn_fold=True,
                                              per_channel=[True, False],
                                              symmetric=[True, False])
        network = quantizer.quantize(network)

    args.logger.info(args.pretrained)
    if os.path.isfile(args.pretrained):
        param_dict = load_checkpoint(args.pretrained)
        param_dict_new = {}
        for key, values in param_dict.items():
            if key.startswith('moments.'):
                continue
            elif key.startswith('yolo_network.'):
                param_dict_new[key[13:]] = values
            else:
                param_dict_new[key] = values
        load_param_into_net(network, param_dict_new)
        args.logger.info('load_model {} success'.format(args.pretrained))
    else:
        args.logger.info('{} not exists or not a pre-trained file'.format(args.pretrained))
        assert FileNotFoundError('{} not exists or not a pre-trained file'.format(args.pretrained))
        exit(1)

    data_root = args.data_root
    ann_file = args.annFile

    ds, data_size = create_yolo_dataset(data_root, ann_file, is_training=False, batch_size=args.per_batch_size,
                                        max_epoch=1, device_num=1, rank=rank_id, shuffle=False,
                                        config=config)

    args.logger.info('testing shape : {}'.format(config.test_img_shape))
    args.logger.info('totol {} images to eval'.format(data_size))

    network.set_train(False)

    detection = DetectionEngine(args)

    input_shape = Tensor(tuple(config.test_img_shape), ms.float32)
    args.logger.info('Start inference....')
    for i, data in enumerate(ds.create_dict_iterator(num_epochs=1)):
        image = data["image"]

        image_shape = data["image_shape"]
        image_id = data["img_id"]

        prediction = network(image, input_shape)
        output_big, output_me, output_small = prediction
        output_big = output_big.asnumpy()
        output_me = output_me.asnumpy()
        output_small = output_small.asnumpy()
        image_id = image_id.asnumpy()
        image_shape = image_shape.asnumpy()

        detection.detect([output_small, output_me, output_big], args.per_batch_size, image_shape, image_id)
        if i % 1000 == 0:
            args.logger.info('Processing... {:.2f}% '.format(i * args.per_batch_size / data_size * 100))

    args.logger.info('Calculating mAP...')
    detection.do_nms_for_results()
    result_file_path = detection.write_result()
    args.logger.info('result file path: {}'.format(result_file_path))
    reveal_type(detection)