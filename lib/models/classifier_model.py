from abc import ABCMeta
from tensorflow_TB.lib.models.model_base import ModelBase
import tensorflow as tf
from tensorflow_TB.lib.base.collections import LOSSES

class ClassifierModel(ModelBase):
    __metaclass__ = ABCMeta
    '''Implementing an image classifier using softmax with cross entropy'''

    def __init__(self, *args, **kwargs):
        super(ClassifierModel, self).__init__(*args, **kwargs)
        self.num_classes         = self.prm.network.NUM_CLASSES
        self.image_height        = self.prm.network.IMAGE_HEIGHT
        self.image_width         = self.prm.network.IMAGE_WIDTH
        self.one_hot_labels      = self.prm.network.ONE_HOT_LABELS
        self.normalize_embedding = self.prm.network.NORMALIZE_EMBEDDING
        self.embedding_dims      = self.prm.network.EMBEDDING_DIMS
        self.num_channels        = self.prm.dataset.NUM_CHANNELS  # number of channels of the input image

        self.xent_cost        = None # contribution of cross entropy to loss
        self.predictions_prob = None # output of the classifier softmax

    def print_stats(self):
        super(ClassifierModel, self).print_stats()
        self.log.info(' NUM_CLASSES: {}'.format(self.num_classes))
        self.log.info(' IMAGE_HEIGHT: {}'.format(self.image_height))
        self.log.info(' IMAGE_WIDTH: {}'.format(self.image_width))
        self.log.info(' ONE_HOT_LABELS: {}'.format(self.one_hot_labels))
        self.log.info(' NORMALIZE_EMBEDDING: {}'.format(self.normalize_embedding))
        self.log.info(' EMBEDDING_DIMS: {}'.format(self.embedding_dims))

    def _set_placeholders(self):
        super(ClassifierModel, self)._set_placeholders()
        self.images = tf.placeholder(tf.float32, [None, self.image_height, self.image_width, self.num_channels])
        if self.one_hot_labels:
            self.labels = tf.placeholder(tf.int32, [None, self.num_classes])
        else:
            self.labels = tf.placeholder(tf.int32, [None])

    def add_fidelity_loss(self):
        with tf.variable_scope('xent_cost'):
            if self.one_hot_labels:
                xent_cost = tf.nn.softmax_cross_entropy_with_logits_v2(logits=self.net['logits'], labels=self.labels)
            else:
                xent_cost = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=self.net['logits'], labels=self.labels)
            xent_cost = tf.reduce_mean(xent_cost, name='cross_entropy_mean')
            self.xent_cost = tf.multiply(self.xent_rate, xent_cost)
            tf.summary.scalar('xent_cost', self.xent_cost)
            xent_assert_op = tf.verify_tensor_all_finite(self.xent_cost, 'xent_cost contains NaN or Inf')
            tf.add_to_collection(LOSSES, self.xent_cost)
            tf.add_to_collection('assertions', xent_assert_op)

    def _build_interpretation(self):
        '''Interprets the logits'''
        self.predictions_prob = tf.nn.softmax(self.net['logits'])
        self.predictions = tf.argmax(self.predictions_prob, axis=1, output_type=tf.int32)
        if self.one_hot_labels:
            labels_int   = tf.argmax(self.labels          , axis=1, output_type=tf.int32)
        else:
            labels_int   = self.labels
        self.score       = tf.reduce_mean(tf.to_float(tf.equal(self.predictions, labels_int)))
