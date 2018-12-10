import os
import cv2
import sys
import tarfile
import numpy as np
import tensorflow as tf
from tensorflow.python.framework import dtypes
from tensorflow.python.framework.ops import convert_to_tensor
try:
    import urllib2 as urllib
except ImportError:
    import urllib.request as urllib


IMAGENET_MEAN = tf.constant([121.55213, 113.84197, 99.50372], dtype=tf.float32)


class ImageDataGenerator(object):
    def __init__(self, txt_file, mode, batch_size, num_classes, shuffle=True, buffer_size=1000):
        """Create a new ImageDataGenerator.
        Recieves a path string to a text file, which consists of many lines,
        where each line has first a path string to an image and seperated by
        a space an integer, referring to the class number. Using this data,
        this class will create TensrFlow datasets, that can be used to train
        e.g. a convolutional neural network.
        Args:
            txt_file: Path to the text file.
            mode: Either 'training' or 'validation'. Depending on this value,
                  different parsing functions will be used.
            batch_size: Number of images per batch.
            num_classes: Number of classes in the dataset.
            shuffle: Wether or not to shuffle the data
                in the dataset and the initial file list.
            buffer_size: Number of images used as buffer for TensorFlows
                shuffling of the dataset.
        Raises:
            ValueError: If an invalid mode is passed.
        """

        self.txt_file = txt_file
        self.num_classes = num_classes

        # retrieve the data from the text file
        self._read_txt_file()

        # number of samples in the dataset
        self.data_size = len(self.labels)

        # initial shuffling of the file and label lists (together!)
        if shuffle:
            self._shuffle_lists()

        # convert lists to TF tensor
        self.img_paths = convert_to_tensor(self.img_paths, dtype=dtypes.string)
        self.labels = convert_to_tensor(self.labels, dtype=dtypes.int32)

        # create dataset
        data = tf.data.Dataset.from_tensor_slices((self.img_paths, self.labels))

        # distinguish between train/infer. when calling the parsing functions
        if mode == 'training':
            data = data.map(self._parse_function_train, num_parallel_calls=20)

        elif mode == 'inference':
            data = data.map(self._parse_function_inference, num_parallel_calls=20)

        else:
            raise ValueError("Invalid mode {}" .format(mode))

        # shuffle the first `buffer_size` elements of the dataset
        if shuffle:
            data = data.shuffle(buffer_size=buffer_size)

        # create a new dataset with batches of images
        data = data.batch(batch_size)
        data = data.repeat()
        iterator = data.make_one_shot_iterator()
        self.iterator = iterator

    def _read_txt_file(self):
        """Read the content of the text file and store it into lists."""
        self.img_paths = []
        self.labels = []
        with open(self.txt_file, 'r') as f:
            lines = f.readlines()
            for line in lines:
                items = line.split(' ')
                self.img_paths.append(items[0])
                self.labels.append(int(items[1]))

    def _shuffle_lists(self):
        """Conjoined shuffling of the list of paths and labels."""
        path = self.img_paths
        labels = self.labels
        permutation = np.random.permutation(self.data_size)
        self.img_paths = []
        self.labels = []
        for i in permutation:
            self.img_paths.append(path[i])
            self.labels.append(labels[i])

    def _parse_function_train(self, filename, label):
        """Input parser for samples of the training set."""
        # convert label number into one-hot-encoding
        one_hot = tf.one_hot(label, self.num_classes)

        # load and preprocess the image
        img_string = tf.read_file(filename)
        img_decoded = tf.image.decode_png(img_string, channels=3)
        img_resized = tf.image.resize_images(img_decoded, [224, 224])   # RGB format
        """
        Dataaugmentation comes here.
        """
        img_centered = tf.subtract(img_resized, IMAGENET_MEAN)  # IMAGENET_MEAN format: RGB

        # RGB -> BGR
        img_bgr = img_centered[:, :, ::-1]

        return img_bgr, one_hot

    def _parse_function_inference(self, filename, label):
        """Input parser for samples of the validation/test set."""
        # convert label number into one-hot-encoding
        one_hot = tf.one_hot(label, self.num_classes)

        # load and preprocess the image
        img_string = tf.read_file(filename)
        img_decoded = tf.image.decode_png(img_string, channels=3)
        img_resized = tf.image.resize_images(img_decoded, [224, 224])
        img_centered = tf.subtract(img_resized, IMAGENET_MEAN)

        # RGB -> BGR
        img_bgr = img_centered[:, :, ::-1]

        return img_bgr, one_hot


def download_and_uncompress_tarball(tarball_url, dataset_dir):
    """Downloads the `tarball_url` and uncompresses it locally.

    Args:
      tarball_url: The URL of a tarball file.
      dataset_dir: The directory where the temporary files are stored.
    """
    filename = tarball_url.split('/')[-1]
    filepath = os.path.join(dataset_dir, filename)

    def _progress(count, block_size, total_size):
        sys.stdout.write('\r>> Downloading %s %.1f%%' % (filename, float(count * block_size) / float(total_size) * 100.0))
        sys.stdout.flush()
    filepath, _ = urllib.request.urlretrieve(tarball_url, filepath, _progress)
    print()
    statinfo = os.stat(filepath)
    print('Successfully downloaded', filename, statinfo.st_size, 'bytes.')
    tarfile.open(filepath, 'r:gz').extractall(dataset_dir)


def download_ckpt(url):
    target_dir = os.path.join("./pre_trained_models/")
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    download_and_uncompress_tarball(url, target_dir)


def compute_mean(train_path="./data/train.txt", validation_path="./data/validation.txt"):
    count = 0
    imgs_mean = np.zeros(shape=(3,), dtype=np.float32)
    for filepath in [train_path, validation_path]:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                img = cv2.imread(line.split(" ")[0])
                img = img.astype(np.float32)
                imgs_mean += np.array([np.mean(img[:, :, 2]), np.mean(img[:, :, 1]), np.mean(img[:, :, 0])])
                count += 1
    IMAGES_MEAN = imgs_mean / count
    print(IMAGES_MEAN)


if __name__ == "__main__":
    compute_mean()