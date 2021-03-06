from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import numpy as np
import os
from sklearn import preprocessing
from tensorflow_TB.lib.datasets.dataset_wrapper import DatasetWrapper
from tensorflow_TB.utils.enums import Mode

class SemiSupervisedDatasetWrapper(DatasetWrapper):
    def __init__(self, *args, **kwargs):
        super(SemiSupervisedDatasetWrapper, self).__init__(*args, **kwargs)

        self.unsupervised_percentage       = self.prm.train.train_control.semi_supervised.UNSUPERVISED_PERCENTAGE
        self.unsupervised_percentage_batch = self.prm.train.train_control.semi_supervised.UNSUPERVISED_PERCENTAGE_BATCH

        self.unpool_set_size               = int(self.unsupervised_percentage * self.train_set_size / 100)
        self.pool_set_size                 = self.train_set_size - self.unpool_set_size

        self.unpool_batch_size             = int(self.unsupervised_percentage_batch * self.train_batch_size / 100)
        self.pool_batch_size               = self.train_batch_size - self.unpool_batch_size

        self.train_unpool_soft_labels      = None
        self.train_unpool_soft_labels_ref  = self.prm.train.train_control.semi_supervised.SOFT_LABELS_REF

        self.train_pool_dataset            = None
        self.train_pool_eval_dataset       = None
        self.train_unpool_dataset          = None
        self.train_unpool_eval_dataset     = None

        self.train_pool_iterator           = None
        self.train_pool_eval_iterator      = None
        self.train_unpool_iterator         = None
        self.train_unpool_eval_iterator    = None

        self.train_pool_handle             = None
        self.train_pool_eval_handle        = None
        self.train_unpool_handle           = None
        self.train_unpool_eval_handle      = None

        self.one_hot_labels = True

    def build(self):
        self.init_soft_labels()
        super(SemiSupervisedDatasetWrapper, self).build()

    def init_soft_labels(self):
        # optionally load train-validation mapping reference reference
        if self.train_unpool_soft_labels_ref is not None:
            self.load_soft_labels()
        else:
            self.set_soft_labels()
        self.save_soft_labels()

    def load_soft_labels(self):
        """Loading self.train_unpool_soft_labels from ref"""
        self.log.info('train_unpool_soft_labels_ref was given. loading numpy {}'.format(self.train_unpool_soft_labels_ref))
        self.train_unpool_soft_labels = np.load(self.train_unpool_soft_labels_ref)
        if self.train_unpool_soft_labels.shape != (self.unpool_set_size, self.num_classes):
            err_str = 'expecting train_unpool_soft_labels.shape={} but got {} instead'\
                .format((self.unpool_set_size, self.num_classes), self.train_unpool_soft_labels.shape)
            self.log.error(err_str)
            raise AssertionError(err_str)

    def set_soft_labels(self):
        """Randomizing self.train_unpool_soft_labels numpy if not loaded from ref"""
        self.log.info('train_unpool_soft_labels_ref is None. Randomizing new probabilities')
        self.train_unpool_soft_labels = np.random.rand(self.unpool_set_size, self.num_classes)
        self.train_unpool_soft_labels = preprocessing.normalize(self.train_unpool_soft_labels, norm='l1')

    def save_soft_labels(self):
        """Saving self.train_unpool_soft_labels into disk"""
        save_path = os.path.join(self.prm.train.train_control.ROOT_DIR, 'soft_labels.npy')
        self.log.info('saving train_unpool_soft_labels to numpy file {}'.format(save_path))
        np.save(save_path, self.train_unpool_soft_labels)

    def set_data_info(self):
        """
        There is no ref to load data info from. Therefore we need to construct a dataset with pool size
        """
        # We start by setting self.train_validation_info as parent
        super(SemiSupervisedDatasetWrapper, self).set_data_info()

        # from all the train samples, choose only pool_set_size samples
        train_indices = self.get_all_train_indices()
        train_pool_indices = self.rand_gen.choice(train_indices, self.pool_set_size, replace=False)
        train_pool_indices = train_pool_indices.tolist()
        train_pool_indices.sort()
        for sample in self.train_validation_info:
            if sample['index'] in train_pool_indices:
                sample['in_pool'] = True

    def get_all_unpool_train_indices(self):
        """
        :return: all unpooled train indices, with 'in_pool'=False
        """
        indices = []
        for sample in self.train_validation_info:
            if sample['dataset'] == 'train' and not sample['in_pool']:
                indices.append(sample['index'])
        indices.sort()
        return indices

    def get_all_pool_train_indices(self):
        """
        :return: all pooled train indices, with 'in_pool'=True
        """
        indices = []
        for sample in self.train_validation_info:
            if sample['dataset'] == 'train' and sample['in_pool']:
                indices.append(sample['index'])
        indices.sort()
        return indices

    def set_datasets(self, X_train, y_train, X_test, y_test):
        super(SemiSupervisedDatasetWrapper, self).set_datasets(X_train, y_train, X_test, y_test)

        # train_pool_set
        train_pool_indices             = self.get_all_pool_train_indices()
        train_pool_images              = X_train[train_pool_indices]
        train_pool_labels              = y_train[train_pool_indices]
        self.train_pool_dataset        = self.set_transform('train_pool'     , Mode.TRAIN, train_pool_indices, train_pool_images, train_pool_labels, self.pool_batch_size)
        self.train_pool_eval_dataset   = self.set_transform('train_pool_eval', Mode.EVAL , train_pool_indices, train_pool_images, train_pool_labels)

        # train_unpool_set
        train_unpool_indices           = self.get_all_unpool_train_indices()
        train_unpool_images            = X_train[train_unpool_indices]
        train_unpool_labels            = y_train[train_unpool_indices]  # never in actual use
        self.train_unpool_dataset      = self.set_transform('train_unpool'     , Mode.TRAIN, train_unpool_indices, train_unpool_images, train_unpool_labels, self.unpool_batch_size)
        self.train_unpool_eval_dataset = self.set_transform('train_unpool_eval', Mode.EVAL , train_unpool_indices, train_unpool_images, train_unpool_labels)

    def build_iterators(self):
        super(SemiSupervisedDatasetWrapper, self).build_iterators()
        self.train_pool_iterator        = self.train_pool_dataset.make_one_shot_iterator()
        self.train_pool_eval_iterator   = self.train_pool_eval_dataset.make_initializable_iterator()
        self.train_unpool_iterator      = self.train_unpool_dataset.make_one_shot_iterator()
        self.train_unpool_eval_iterator = self.train_unpool_eval_dataset.make_initializable_iterator()

    def set_handles(self, sess):
        super(SemiSupervisedDatasetWrapper, self).set_handles(sess)
        self.train_pool_handle        = sess.run(self.train_pool_iterator.string_handle())
        self.train_pool_eval_handle   = sess.run(self.train_pool_eval_iterator.string_handle())
        self.train_unpool_handle      = sess.run(self.train_unpool_iterator.string_handle())
        self.train_unpool_eval_handle = sess.run(self.train_unpool_eval_iterator.string_handle())

    def get_handle(self, name):
        if name == 'train_pool':
            return self.train_pool_handle
        elif name == 'train_pool_eval':
            return self.train_pool_eval_handle
        elif name == 'train_unpool':
            return self.train_unpool_handle
        elif name == 'train_unpool_eval':
            return self.train_unpool_eval_handle
        return super(SemiSupervisedDatasetWrapper, self).get_handle(name)

    def print_stats(self):
        super(SemiSupervisedDatasetWrapper, self).print_stats()
        self.log.info(' UNSUPERVISED_PERCENTAGE: {}'.format(self.unsupervised_percentage))
        self.log.info(' UNSUPERVISED_PERCENTAGE_BATCH: {}'.format(self.unsupervised_percentage_batch))
        self.log.info(' SOFT_LABELS_REF: {}'.format(self.train_unpool_soft_labels_ref))

    def update_soft_labels(self, new_soft_labels, step):
        """
        :param new_soft_labels: updating the tain_unpooled soft labels
        :param step: gloabl step
        :return: None
        """
        if new_soft_labels.shape != self.train_unpool_soft_labels.shape:
            err_str = 'new_soft_labels.shape does not match self.train_unpool_soft_labels.shape. ({}!={})'\
                .format(new_soft_labels.shape, self.train_unpool_soft_labels.shape)
            self.log.error(err_str)
            raise AssertionError(err_str)

        sampled_old_values = self.train_unpool_soft_labels[0:5]
        self.log.info('updating the train_unpool soft labels for global_step={}'.format(step))
        self.train_unpool_soft_labels = new_soft_labels

        debug_str = 'first 5 train unpooled soft labels:\n old_values = {}\n new_values = {}'\
            .format(sampled_old_values, self.train_unpool_soft_labels[0:5])
        self.log.info(debug_str)
        print(debug_str)

        self.save_soft_labels()

    def fetch_soft_labels(self, batch_unpool_indices):
        """
        :param train_unpool_indices: train_unpool_indices as randomized from get_mini_batch
        :return: The relative indices in the soft_labels matrix
        """
        if len(batch_unpool_indices) != self.unpool_batch_size:
            err_str = 'len(batch_unpool_indices) != self.unpool_batch_size ({} != {})'\
                .format(len(batch_unpool_indices), self.unpool_batch_size)
            self.log.error(err_str)
            raise AssertionError(err_str)

        train_unpool_indices = self.get_all_unpool_train_indices()
        soft_labels = np.zeros([self.unpool_batch_size, self.num_classes])
        for i, j in enumerate(batch_unpool_indices):
            soft_labels[i] = self.train_unpool_soft_labels[train_unpool_indices.index(j)]
        return soft_labels

    @property
    def pool_size(self):
        return len(self.get_all_pool_train_indices())

    @property
    def unpool_size(self):
        return len(self.get_all_unpool_train_indices())

