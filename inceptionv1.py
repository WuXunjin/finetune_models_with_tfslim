import os
import tensorflow as tf
from nets import inception
from tensorflow.python import pywrap_tensorflow
from tensorflow.contrib.slim import arg_scope


class InceptionV1(object):
    def __init__(self, num_classes, train_layers, learning_rate=0.001, model="train", weights_path='DEFAULT'):
        """Create the graph of the inceptionv1 model.
        """
        # Parse input arguments into class variables
        if weights_path == 'DEFAULT':
            self.WEIGHTS_PATH = "./checkpoints/inception_v1.ckpt"
        else:
            self.WEIGHTS_PATH = weights_path
        self.train_layers = train_layers

        with tf.variable_scope("input"):
            self.image_size = inception.inception_v1.default_image_size
            self.x_input = tf.placeholder(tf.float32, [None, self.image_size, self.image_size, 3], name="x_input")
            self.y_input = tf.placeholder(tf.float32, [None, num_classes], name="y_input")
            self.keep_prob = tf.placeholder(tf.float32, name="keep_prob")

        with arg_scope(inception.inception_v1_arg_scope()):

            self.logits, _ = inception.inception_v1(self.x_input, num_classes=num_classes, is_training=True)

        if model == "train" or model == "val":

            with tf.name_scope("loss"):
                self.loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits_v2(logits=self.logits, labels=self.y_input))

            with tf.name_scope("train"):
                self.global_step = tf.Variable(0, name="global_step", trainable=False)
                var_list = [v for v in tf.trainable_variables() if v.name.split('/')[-2] in train_layers or v.name.split('/')[-3] in train_layers ]
                gradients = tf.gradients(self.loss, var_list)
                self.grads_and_vars = list(zip(gradients, var_list))
                optimizer = tf.train.GradientDescentOptimizer(learning_rate)
                self.train_op = optimizer.apply_gradients(grads_and_vars=self.grads_and_vars, global_step=self.global_step)

            with tf.name_scope("probability"):
                self.probability = tf.nn.softmax(self.logits, name="probability")

            with tf.name_scope("prediction"):
                self.prediction = tf.argmax(self.logits, 1, name="prediction")

            with tf.name_scope("accuracy"):
                correct_prediction = tf.equal(self.prediction, tf.argmax(self.y_input, 1))
                self.accuracy = tf.reduce_mean(tf.cast(correct_prediction, "float"), name="accuracy")

    def load_initial_weights(self, session):

        checkpoint_path = os.path.join("./pre_trained_models", "inception_v1.ckpt")
        reader = pywrap_tensorflow.NewCheckpointReader(checkpoint_path)

        # Load the weights into memory
        var_to_shape_map = reader.get_variable_to_shape_map()

        for op_name in var_to_shape_map:
            # Do not load variable: global_step for finetuning
            if op_name == "global_step":
                continue

            for layer in self.train_layers:
                if layer not in op_name:
                    with tf.variable_scope("/".join(op_name.split("/")[0:-1]), reuse=True):

                        data = reader.get_tensor(op_name)

                        var = tf.get_variable(op_name.split("/")[-1], trainable=False)
                        session.run(var.assign(data))