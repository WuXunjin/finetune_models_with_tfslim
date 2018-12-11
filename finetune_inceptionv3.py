import os
import time
import datetime
import tensorflow as tf
from inceptionv3 import InceptionV3
from utils import ImageDataGenerator
from utils import download_ckpt

os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3'

"""
Configuration Part.
"""
# Parameters
tf.app.flags.DEFINE_string("train_file", './data/train.txt', "the path of train data")
tf.app.flags.DEFINE_string("val_file", './data/validation.txt', "the path of val data")
tf.app.flags.DEFINE_float("learning_rate", 0.001, "learn_rate(default:0.001)")
tf.app.flags.DEFINE_integer("num_epochs", 50, "num_epoches(default:10)")
tf.app.flags.DEFINE_integer("batch_size", 128, "batch_size(default:128)")
tf.app.flags.DEFINE_integer("num_classes", 5, "num_classes(default:2)")
tf.app.flags.DEFINE_float("keep_prob", 0.8, "dropout_rate(default:0.8)")
tf.app.flags.DEFINE_integer("evaluate_every", 200, "Evaluate model on dev set after this many steps (default: 100)")
tf.app.flags.DEFINE_integer("checkpoint_every", 400, "Save model after this many steps (default: 100)")
tf.app.flags.DEFINE_integer("num_checkpoints", 3, "num_checkpoints(default:3)")
FLAGS = tf.app.flags.FLAGS
train_layers = ["Conv2d_1c_1x1", "Conv2d_2b_1x1"]

"""
Main Part of the finetuning Script.
"""
# Load data on the cpu
print("Loading data...")
with tf.device('/cpu:0'):
    train_iterator = ImageDataGenerator(txt_file=FLAGS.train_file,
                                        mode='training',
                                        batch_size=FLAGS.batch_size,
                                        num_classes=FLAGS.num_classes,
                                        shuffle=True)

    val_iterator = ImageDataGenerator(txt_file=FLAGS.val_file,
                                      mode='inference',
                                      batch_size=FLAGS.batch_size,
                                      num_classes=FLAGS.num_classes,
                                      shuffle=False)

    train_next_batch = train_iterator.iterator.get_next()
    val_next_batch = val_iterator.iterator.get_next()


# Initialize model
inceptionv3 = InceptionV3(num_classes=FLAGS.num_classes,
                          train_layers=train_layers,
                          learning_rate=FLAGS.learning_rate,
                          model="train"
                          )

with tf.Session() as sess:
    timestamp = str(int(time.time()))
    out_dir = os.path.abspath(os.path.join(os.path.curdir, "runs", "inceptionv3", timestamp))
    print("Writing to {}\n".format(out_dir))

    # define summary
    grad_summaries = []
    for g, v in inceptionv3.grads_and_vars:
        if g is not None:
            grad_hist_summary = tf.summary.histogram("{}/grad/hist".format(v.name), g)
            sparsity_summary = tf.summary.scalar("{}/grad/sparsity".format(v.name), tf.nn.zero_fraction(g))
            grad_summaries.append(grad_hist_summary)
            grad_summaries.append(sparsity_summary)
    grad_summaries_merged = tf.summary.merge(grad_summaries)
    loss_summary = tf.summary.scalar("loss", inceptionv3.loss)
    acc_summary = tf.summary.scalar("accuracy", inceptionv3.accuracy)

    # merge all the train summary
    train_summary_merged = tf.summary.merge([loss_summary, acc_summary, grad_summaries_merged])
    train_summary_writer = tf.summary.FileWriter(os.path.join(out_dir, "summaries", "train"), graph=sess.graph)
    # merge all the dev summary
    val_summary_merged = tf.summary.merge([loss_summary, acc_summary])
    val_summary_writer = tf.summary.FileWriter(os.path.join(out_dir, "summaries", "val"), graph=sess.graph)

    # checkPoint saver
    checkpoint_dir = os.path.abspath(os.path.join(out_dir, "ckpt"))
    if not os.path.exists(checkpoint_dir):
        os.makedirs(checkpoint_dir)
    checkpoint_prefix = os.path.join(checkpoint_dir, "model")
    saver = tf.train.Saver(tf.global_variables(), max_to_keep=FLAGS.num_checkpoints)

    sess.run(tf.global_variables_initializer())

    # Load the pre_trained weights into the non-trainable layer
    if "inception_v3.ckpt" not in os.listdir("./pre_trained_models/"):
        print(" ")
        download_ckpt(url="http://download.tensorflow.org/models/inception_v3_2016_08_28.tar.gz")

    inceptionv3.load_initial_weights(sess)
    print("run the tensorboard in terminal: \ntensorboard --logdir={} --port=6006 \n".format(out_dir))

    exit()
    while True:
        # train loop
        x_batch_train, y_batch_train = sess.run(train_next_batch)
        _, step, train_summaries, loss, accuracy = sess.run([inceptionv3.train_op, inceptionv3.global_step, train_summary_merged, inceptionv3.loss, inceptionv3.accuracy],
                                                            feed_dict={
                                                                inceptionv3.x_input: x_batch_train,
                                                                inceptionv3.y_input: y_batch_train,
                                                                inceptionv3.keep_prob: FLAGS.keep_prob
                                                            })
        train_summary_writer.add_summary(train_summaries, step)
        time_str = datetime.datetime.now().isoformat()
        print("{}: step: {}, loss: {:g}, acc: {:g}".format(time_str, step, loss, accuracy))

        # validation
        current_step = tf.train.global_step(sess, inceptionv3.global_step)

        if current_step % FLAGS.evaluate_every == 0:
            print("\nEvaluation:")
            x_batch_val, y_batch_val = sess.run(val_next_batch)
            step, dev_summaries, loss, accuracy = sess.run([inceptionv3.global_step, val_summary_merged, inceptionv3.loss, inceptionv3.accuracy],
                                                           feed_dict={
                                                               inceptionv3.x_input: x_batch_val,
                                                               inceptionv3.y_input: y_batch_val,
                                                               inceptionv3.keep_prob: 1
                                                           })
            val_summary_writer.add_summary(dev_summaries, step)
            time_str = datetime.datetime.now().isoformat()
            print("{}: step: {}, loss: {:g}, acc: {:g}".format(time_str, step, loss, accuracy))
            print("\n")

        if current_step % FLAGS.checkpoint_every == 0:
            path = saver.save(sess, checkpoint_prefix, global_step=current_step)
            print("Saved model checkpoint to {}\n".format(path))

        # break conditon
        #if accuracy > 0.95:
        #exit()





