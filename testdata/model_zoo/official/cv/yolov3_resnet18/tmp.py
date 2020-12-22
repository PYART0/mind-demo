import os
import argparse
import time
from mindspore import context, Tensor
from mindspore.train.serialization import load_checkpoint, load_param_into_net
from src.yolov3 import yolov3_resnet18, YoloWithEval
from src.dataset import create_yolo_dataset, data_to_mindrecord_byte_image
from src.config import ConfigYOLOV3ResNet18
from src.utils import metrics

def yolo_eval(dataset_path, ckpt_path):

    ds = create_yolo_dataset(dataset_path, is_training=False)
    config = ConfigYOLOV3ResNet18()
    net = yolov3_resnet18(config)
    eval_net = YoloWithEval(net, config)
    print("Load Checkpoint!")
    param_dict = load_checkpoint(ckpt_path)
    load_param_into_net(net, param_dict)


    eval_net.set_train(False)
    i = 1.
    total = ds.get_dataset_size()
    start = time.time()
    pred_data = []
    print("\n========================================\n")
    print("total images num: ", total)
    print("Processing, please wait a moment.")
    for data in ds.create_dict_iterator(output_numpy=True, num_epochs=1):
        img_np = data['image']
        image_shape = data['image_shape']
        annotation = data['annotation']

        eval_net.set_train(False)
        output = eval_net(Tensor(img_np), Tensor(image_shape))
        for batch_idx in range(img_np.shape[0]):
            pred_data.append({"boxes": output[0].asnumpy()[batch_idx],
                              "box_scores": output[1].asnumpy()[batch_idx],
                              "annotation": annotation})
        percent = round(i / total * 100, 2)

        print('    %s [%d/%d]' % (str(percent) + '%', i, total), end='\r')
        i += 1
    print('    %s [%d/%d] cost %d ms' % (str(100.0) + '%', total, total, int((time.time() - start) * 1000)), end='\n')

    precisions, recalls = metrics(pred_data)
    print("\n========================================\n")
    for i in range(config.num_classes):
        print("class {} precision is {:.2f}%, recall is {:.2f}%".format(i, precisions[i] * 100, recalls[i] * 100))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Yolov3 evaluation')
    parser.add_argument("--device_id", type=int, default=0, help="Device id, default is 0.")
    parser.add_argument("--mindrecord_dir", type=str, default="./Mindrecord_eval",
                        help="Mindrecord directory. If the mindrecord_dir is empty, it wil generate mindrecord file by"
                             "image_dir and anno_path. Note if mindrecord_dir isn't empty, it will use mindrecord_dir "
                             "rather than image_dir and anno_path. Default is ./Mindrecord_eval")
    parser.add_argument("--image_dir", type=str, default="", help="Dataset directory, "
                                                                  "the absolute image path is joined by the image_dir "
                                                                  "and the relative path in anno_path.")
    parser.add_argument("--anno_path", type=str, default="", help="Annotation path.")
    parser.add_argument("--ckpt_path", type=str, required=True, help="Checkpoint path.")
    args_opt = parser.parse_args()

    context.set_context(mode=context.GRAPH_MODE, device_target="Ascend", device_id=args_opt.device_id)

    if not os.path.isdir(args_opt.mindrecord_dir):
        os.makedirs(args_opt.mindrecord_dir)

    yolo_prefix = "yolo.mindrecord"
    mindrecord_file = os.path.join(args_opt.mindrecord_dir, yolo_prefix + "0")
    reveal_type(os.path)