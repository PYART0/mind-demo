import mindspore.common.dtype as mstype
import mindspore.dataset.engine as de
import mindspore.dataset.vision.c_transforms as C
import mindspore.dataset.transforms.c_transforms as C2


def create_dataset(dataset_path, do_train, config, device_target, repeat_num=1, batch_size=32, run_distribute=False):
    if device_target == "GPU":
        if do_train:
            if run_distribute:
                from mindspore.communication.management import get_rank, get_group_size
                ds = de.ImageFolderDataset(dataset_path, num_parallel_workers=8, shuffle=True,
                                           num_shards=get_group_size(), shard_id=get_rank())
            else:
                ds = de.ImageFolderDataset(dataset_path, num_parallel_workers=8, shuffle=True)
        else:
            ds = de.ImageFolderDataset(dataset_path, num_parallel_workers=8, shuffle=True)
    else:
        raise ValueError("Unsupported device_target.")

    resize_height = config.image_height
    resize_width = config.image_width
    buffer_size = 1000

    decode_op = C.Decode()
    resize_crop_op = C.RandomCropDecodeResize(resize_height, scale=(0.08, 1.0), ratio=(0.75, 1.333))
    horizontal_flip_op = C.RandomHorizontalFlip(prob=0.5)

    resize_op = C.Resize(256)
    center_crop = C.CenterCrop(resize_width)
    reveal_type(C)