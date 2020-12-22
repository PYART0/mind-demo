import os
import argparse
import time
import numpy as np
from pycocotools.coco import COCO
from mindspore import context, Tensor
from mindspore.train.serialization import load_checkpoint, load_param_into_net
from mindspore.common import set_seed

from src.maskrcnn_mobilenetv1.mask_rcnn_mobilenetv1 import Mask_Rcnn_Mobilenetv1
from src.config import config
from src.dataset import data_to_mindrecord_byte_image, create_maskrcnn_dataset
from src.util import coco_eval, bbox2result_1image, results2json, get_seg_masks

set_seed(1)

parser = argparse.ArgumentParser(description="MaskRcnn evaluation")
parser.add_argument("--dataset", type=str, default="coco", help="Dataset, default is coco.")
parser.add_argument("--ann_file", type=str, default="val.json", help="Ann file, default is val.json.")
parser.add_argument("--checkpoint_path", type=str, required=True, help="Checkpoint file path.")
parser.add_argument("--device_id", type=int, default=0, help="Device id, default is 0.")
args_opt = parser.parse_args()

context.set_context(mode=context.GRAPH_MODE, device_target="Ascend", device_id=args_opt.device_id)

def MaskRcnn_eval(dataset_path, ckpt_path, ann_file):
    ds = create_maskrcnn_dataset(dataset_path, batch_size=config.test_batch_size, is_training=False)

    net = Mask_Rcnn_Mobilenetv1(config)
    param_dict = load_checkpoint(ckpt_path)
    load_param_into_net(net, param_dict)
    net.set_train(False)

    eval_iter = 0
    total = ds.get_dataset_size()
    outputs = []
    dataset_coco = COCO(ann_file)

    print("\n========================================\n")
    print("total images num: ", total)
    print("Processing, please wait a moment.")
    max_num = 128

    for data in ds.create_dict_iterator(output_numpy=True, num_epochs=1):
        img_data = data['image']
        img_metas = data['image_shape']
        gt_bboxes = data['box']
        gt_labels = data['label']
        gt_num = data['valid_num']
        gt_mask = data["mask"]

        start = time.time()
        output = net(Tensor(img_data), Tensor(img_metas), Tensor(gt_bboxes), Tensor(gt_labels), Tensor(gt_num),
                     Tensor(gt_mask))
        end = time.time()
        print("Iter {} cost time {}".format(eval_iter, end - start))

        all_bbox = output[0]
        all_label = output[1]
        all_mask = output[2]
        all_mask_fb = output[3]

        for j in range(config.test_batch_size):
            all_bbox_squee = np.squeeze(all_bbox.asnumpy()[j, :, :])
            all_label_squee = np.squeeze(all_label.asnumpy()[j, :, :])
            all_mask_squee = np.squeeze(all_mask.asnumpy()[j, :, :])
            all_mask_fb_squee = np.squeeze(all_mask_fb.asnumpy()[j, :, :, :])

            all_bboxes_tmp_mask = all_bbox_squee[all_mask_squee, :]
            all_labels_tmp_mask = all_label_squee[all_mask_squee]
            all_mask_fb_tmp_mask = all_mask_fb_squee[all_mask_squee, :, :]

            if all_bboxes_tmp_mask.shape[0] > max_num:
                inds = np.argsort(-all_bboxes_tmp_mask[:, -1])
                inds = inds[:max_num]
                all_bboxes_tmp_mask = all_bboxes_tmp_mask[inds]
                all_labels_tmp_mask = all_labels_tmp_mask[inds]
                all_mask_fb_tmp_mask = all_mask_fb_tmp_mask[inds]


            bbox_results = bbox2result_1image(all_bboxes_tmp_mask, all_labels_tmp_mask, config.num_classes)
            segm_results = get_seg_masks(all_mask_fb_tmp_mask, all_bboxes_tmp_mask, all_labels_tmp_mask, img_metas[j],
                                         True, config.num_classes)
            outputs.append((bbox_results, segm_results))

        eval_iter = eval_iter + 1

    eval_types = ["bbox", "segm"]
    result_files = results2json(dataset_coco, outputs, "./results.pkl")
    coco_eval(result_files, eval_types, dataset_coco, single_result=False)

if __name__ == '__main__':
    prefix = "MaskRcnn_eval.mindrecord"
    mindrecord_dir = config.mindrecord_dir
    mindrecord_file = os.path.join(mindrecord_dir, prefix)
    if not os.path.exists(mindrecord_file):
        if not os.path.isdir(mindrecord_dir):
            reveal_type(os)