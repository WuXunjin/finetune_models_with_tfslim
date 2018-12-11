import os
import tensorflow as tf
from inceptionv3 import InceptionV3
from utils import ImageDataGenerator

os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3'

"""
Configuration Part.
"""
# Parameters
tf.app.flags.DEFINE_string("test_file", './data/test.txt', "the path of test data")
tf.app.flags.DEFINE_integer("batch_size", 128, "batch_size(default:128)")
tf.app.flags.DEFINE_integer("num_classes", 5, "num_classes(default:2)")
tf.app.flags.DEFINE_float("test_keep_prob", 1.0, "test_dropout_keep_rate(default:1.0)")
FLAGS = tf.app.flags.FLAGS
train_layers = ["Conv2d_1c_1x1"]

# Load data on the cpu
print("Loading data...")
with tf.device('/cpu:0'):
    test_iterator = ImageDataGenerator(txt_file=FLAGS.test_file,
                                       mode='inference',
                                       batch_size=FLAGS.batch_size,
                                       num_classes=FLAGS.num_classes,
                                       shuffle=True)
    test_next_batch = test_iterator.iterator.get_next()


# Initialize model
inceptionv3 = InceptionV3(num_classes=FLAGS.num_classes, train_layers=train_layers, model="test")


with tf.Session() as sess:

    sess.run(tf.global_variables_initializer())

    saver = tf.train.Saver(var_list=tf.global_variables())
    model_file = tf.train.latest_checkpoint("./runs/inceptionv3/1544497939/ckpt/")
    saver.restore(sess, model_file)

    x_batch_test, y_batch_test = sess.run(test_next_batch)
    accuracy = sess.run(inceptionv3.accuracy, feed_dict={inceptionv3.x_input: x_batch_test,
                                                         inceptionv3.y_input: y_batch_test,
                                                         inceptionv3.keep_prob: FLAGS.test_keep_prob
                                                         }
                        )
    print(accuracy)
