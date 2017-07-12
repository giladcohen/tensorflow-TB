
"""ResNet Train/Eval module.
"""
from __future__ import print_function


import time
import six
import sys
import os
dirname=os.path.dirname
cwd = os.getcwd()        #Resnet_KNN
pardir = dirname(cwd)    #workspace
sys.path.insert(0, cwd)
print ('cwd = %s' % cwd)
import numpy as np
import lib.resnet_model as resnet_model
import tensorflow as tf
from keras.datasets import cifar10, cifar100 # for debug
import matplotlib.pyplot as plt #for debug
import lib.active_kmean as active_kmean
from lib.data_tank import DataTank
from lib.active_data_tank import ActiveDataTank
from sklearn.neighbors import NearestNeighbors
import os
from math import ceil

flags = tf.app.flags
FLAGS = flags.FLAGS
flags.DEFINE_float('learning_rate', 0.01, 'Initial learning rate.')
flags.DEFINE_string('dataset', 'cifar10', 'cifar10 or cifar100.')
flags.DEFINE_string('mode', 'train', 'train or eval.')
flags.DEFINE_string('train_data_dir',    os.path.join(pardir, 'cifar10_data/train_data'),       'dir for training data.')
flags.DEFINE_string('train_labels_file', os.path.join(pardir, 'cifar10_data/train_labels.txt'), 'file for training labels.')
flags.DEFINE_string('eval_data_dir',     os.path.join(pardir, 'cifar10_data/test_data'),        'dir for evaluation data.')
flags.DEFINE_string('eval_labels_file',  os.path.join(pardir, 'cifar10_data/test_labels.txt'),  'file for evaluation labels.')
flags.DEFINE_integer('image_size', 32, 'Image side length.')
flags.DEFINE_bool('eval_once', False, 'Whether evaluate the model only once.')
flags.DEFINE_string('log_root', '',
                           'Directory to keep the checkpoints. Should be a '
                           'parent directory of FLAGS.train_dir/eval_dir.')
flags.DEFINE_integer('num_gpus', 0, 'Number of gpus used for training. (0 or 1)')
flags.DEFINE_string('learn_mode', 'passive', 'Choose between active/rand_steps/passive')
flags.DEFINE_integer('batch_size', -1, 'batch size for train/test')
flags.DEFINE_integer('clusters', 100, 'batch size for train/test')
flags.DEFINE_integer('cap', 50000, 'batch size for train/test')
flags.DEFINE_integer('active_epochs', 50, 'number of epochs for every pool iteration')


TRAIN_DIR = os.path.join(FLAGS.log_root, 'train')
EVAL_DIR  = os.path.join(FLAGS.log_root, 'test')
TRAIN_SET_SIZE = 50000
TEST_SET_SIZE  = 10000

if FLAGS.dataset   == 'cifar10':
    NUM_CLASSES = 10
elif FLAGS.dataset == 'cifar100':
    NUM_CLASSES = 100
else:
    raise NameError('Test does not support %s dataset' %FLAGS.dataset)

if FLAGS.batch_size != -1:
    TRAIN_BATCH_SIZE = EVAL_BATCH_SIZE = FLAGS.batch_size
else:
    TRAIN_BATCH_SIZE = 270
    EVAL_BATCH_SIZE  = 2200

# for evaluation analysis:
TRAIN_BATCH_COUNT     = int(ceil(1.0 * TRAIN_SET_SIZE / EVAL_BATCH_SIZE))
LAST_TRAIN_BATCH_SIZE = TRAIN_SET_SIZE % EVAL_BATCH_SIZE
EVAL_BATCH_COUNT      = int(ceil(1.0 * TEST_SET_SIZE  / EVAL_BATCH_SIZE))
LAST_EVAL_BATCH_SIZE  = TEST_SET_SIZE % EVAL_BATCH_SIZE

def train(hps):
    """Training loop."""
    """Training loop. Step1 - selecting TRAIN_BATCH randomized images"""
    dt = ActiveDataTank(n_clusters=FLAGS.clusters,
                        data_path=FLAGS.train_data_dir,
                        label_file=FLAGS.train_labels_file,
                        batch_size=TRAIN_BATCH_SIZE,
                        N=TRAIN_SET_SIZE,
                        to_preprocess=True)

    images_ph      = tf.placeholder(tf.float32, [None, FLAGS.image_size, FLAGS.image_size, 3])
    labels_ph      = tf.placeholder(tf.int32,   [None])
    is_training_ph = tf.placeholder(tf.bool)

    labels_1hot = tf.one_hot(labels_ph, NUM_CLASSES)

    model = resnet_model.ResNet(hps, images_ph, labels_1hot, is_training_ph)
    model.set_params()
    model.build_graph()

    param_stats = tf.contrib.tfprof.model_analyzer.print_model_analysis(
        tf.get_default_graph(),
        tfprof_options=tf.contrib.tfprof.model_analyzer.
            TRAINABLE_VARS_PARAMS_STAT_OPTIONS)
    sys.stdout.write('total_params: %d\n' % param_stats.total_parameters)

    tf.contrib.tfprof.model_analyzer.print_model_analysis(
        tf.get_default_graph(),
        tfprof_options=tf.contrib.tfprof.model_analyzer.FLOAT_OPS_OPTIONS)

    truth = tf.argmax(model.labels, axis=1)
    predictions = tf.argmax(model.predictions, axis=1)
    precision = tf.reduce_mean(tf.to_float(tf.equal(predictions, truth)))

    images_summary = tf.summary.image('images', images_ph, max_outputs=3)

    summary_hook = tf.train.SummarySaverHook(
        save_steps=10, #was 100
        #save_secs = 60,
        output_dir=TRAIN_DIR,
        summary_op=tf.summary.merge([model.summaries,
                                     images_summary,
                                     tf.summary.scalar('Precision', precision)]))

    logging_hook = tf.train.LoggingTensorHook(
        tensors={'step': model.global_step,
                 'loss_xent': model.xent_cost,
                 'loss_wd': model.wd_cost,
                 'loss': model.cost,
                 'precision': precision},
        every_n_iter=10) #was 100

    class _LearningRateSetterHook(tf.train.SessionRunHook):
        """Sets learning_rate based on global step."""

        def begin(self):
            self._lrn_rate = FLAGS.learning_rate

        def before_run(self, run_context):
            return tf.train.SessionRunArgs(
                model.global_step,  # Asks for global step value.
                feed_dict={model.lrn_rate: self._lrn_rate})  # Sets learning rate

        def after_run(self, run_context, run_values):
            train_step = run_values.results
            epoch = (TRAIN_BATCH_SIZE * train_step) // FLAGS.cap
            # if FLAGS.learn_mode in ['active', 'rand_steps']:
            #     epoch = (TRAIN_BATCH_SIZE * train_step) // FLAGS.cap
            # else:
            #     epoch = (TRAIN_BATCH_SIZE * train_step) // TRAIN_SET_SIZE #passive learning
            if epoch < 60:
                self._lrn_rate = FLAGS.learning_rate
            elif epoch < 120:
                self._lrn_rate = FLAGS.learning_rate/5
            elif epoch < 160:
                self._lrn_rate = FLAGS.learning_rate/25
            else:
                self._lrn_rate = FLAGS.learning_rate/125

    sess = tf.train.MonitoredTrainingSession(
            checkpoint_dir=FLAGS.log_root,
            hooks=[logging_hook, _LearningRateSetterHook()],
            chief_only_hooks=[summary_hook],
            # Since we provide a SummarySaverHook, we need to disable default
            # SummarySaverHook. To do that we set save_summaries_steps to 0.
            save_summaries_steps=0,
            save_checkpoint_secs=60, # was 600
            config=tf.ConfigProto(allow_soft_placement=True))

    if FLAGS.learn_mode == 'passive':
        while len(dt.pool) < FLAGS.cap:
            dt.update_pool_rand()
        assert len(dt.pool) == FLAGS.cap, "pool size does not equal exactly cap=%0d for passive learn" % FLAGS.cap
        while not sess.should_stop():
            images, labels, images_aug, labels_aug = dt.fetch_batch()
            sess.run(model.train_op, feed_dict={images_ph: images_aug,
                                                labels_ph: labels_aug,
                                                is_training_ph: True})

    elif FLAGS.learn_mode == 'rand_steps':
        while not sess.should_stop():
            lp = len(dt.pool)
            if lp == FLAGS.cap:
                images, labels, images_aug, labels_aug = dt.fetch_batch()
                sess.run(model.train_op, feed_dict={images_ph: images_aug,
                                                    labels_ph: labels_aug,
                                                    is_training_ph: True})
            else:
                steps_to_go = int(np.round(FLAGS.active_epochs * float(lp) / TRAIN_BATCH_SIZE))
                for i in range(steps_to_go):
                    images, labels, images_aug, labels_aug = dt.fetch_batch()
                    sess.run(model.train_op, feed_dict={images_ph: images_aug,
                                                        labels_ph: labels_aug,
                                                        is_training_ph: True})
                dt.update_pool_rand()

    elif FLAGS.learn_mode == 'active':
        while not sess.should_stop():
            lp = len(dt.pool)
            if lp == FLAGS.cap:
                images, labels, images_aug, labels_aug = dt.fetch_batch()
                sess.run(model.train_op, feed_dict={images_ph: images_aug,
                                                    labels_ph: labels_aug,
                                                    is_training_ph: True})
            else:
                steps_to_go = int(np.round(FLAGS.active_epochs * float(lp) / TRAIN_BATCH_SIZE))
                for i in range(steps_to_go):
                    images, labels, images_aug, labels_aug = dt.fetch_batch()
                    sess.run(model.train_op, feed_dict={images_ph: images_aug,
                                                        labels_ph: labels_aug,
                                                        is_training_ph: True})

                # analyzing (evaluation)
                fc1_vec = -1.0 * np.ones((TRAIN_SET_SIZE, 640), dtype=np.float32)
                total_samples = 0 #for debug
                print ('start storing feature maps for the entire train set')
                for i in range(TRAIN_BATCH_COUNT):
                    b = i * EVAL_BATCH_SIZE
                    if i < (TRAIN_BATCH_COUNT - 1) or (LAST_TRAIN_BATCH_SIZE == 0):
                        e = (i + 1) * EVAL_BATCH_SIZE
                    else:
                        e = i * EVAL_BATCH_SIZE + LAST_TRAIN_BATCH_SIZE
                    images, labels, _, _ = dt.fetch_batch_common(indices=range(b,e))
                    net = sess.run(model.net, feed_dict={images_ph: images,
                                                         labels_ph: labels,
                                                         is_training_ph: False})
                    fc1_vec[b:e] = np.reshape(net['pool_out'], (e - b, 640))
                    total_samples += images.shape[0] #debug
                    print ('Storing completed: %0d%%' %(int(100.0*float(e)/TRAIN_SET_SIZE)))
                assert np.sum(fc1_vec == -1) == 0 #debug
                assert total_samples == TRAIN_SET_SIZE, \
                    'total_samples equals %0d instead of %0d' % (total_samples, TRAIN_SET_SIZE) #debug

                KM = active_kmean.KMeansWrapper(fixed_centers=fc1_vec[dt.pool], n_clusters=lp + FLAGS.clusters, init='k-means++', n_init=1,
                                                max_iter=300000, tol=1e-4, precompute_distances='auto',
                                                verbose=0, random_state=None, copy_x=True,
                                                n_jobs=1, algorithm='auto')
                centers = KM.fit_predict_centers(fc1_vec)
                new_centers = centers[lp:(lp + FLAGS.clusters)]
                nbrs = NearestNeighbors(n_neighbors=1)
                nbrs.fit(fc1_vec)
                indices = nbrs.kneighbors(new_centers, return_distance=False)

                indices = indices.T[0].tolist()
                already_pooled_cnt = 0 # number of indices of samples that we added to pool already
                for myItem in indices:
                    if myItem in dt.pool:
                        already_pooled_cnt += 1
                        indices.remove(myItem)
                        print('Removing value %0d from indices because it already exists in pool' % myItem)
                print('%0d indices were already in pool. Randomized indices will be chosen instead of them' % already_pooled_cnt)
                dt.update_pool(indices)
                dt.update_pool_rand(n_clusters=already_pooled_cnt)
                #end of analysis

def evaluate(hps):
    """Eval loop."""

    dt = DataTank(data_path=FLAGS.eval_data_dir,
                  label_file=FLAGS.eval_labels_file,
                  batch_size=EVAL_BATCH_SIZE,
                  N=TEST_SET_SIZE,
                  to_preprocess=False)

    images_ph      = tf.placeholder(tf.float32, [None, FLAGS.image_size, FLAGS.image_size, 3])
    labels_ph      = tf.placeholder(tf.int32,   [None])
    is_training_ph = tf.placeholder(tf.bool)

    labels_1hot = tf.one_hot(labels_ph, NUM_CLASSES)

    model = resnet_model.ResNet(hps, images_ph, labels_1hot, is_training_ph)
    model.set_params()
    model.build_graph()

    saver = tf.train.Saver()
    summary_writer = tf.summary.FileWriter(EVAL_DIR)

    sess = tf.Session(config=tf.ConfigProto(allow_soft_placement=True))

    best_precision = 0.0
    while True:
        try:
            ckpt_state = tf.train.get_checkpoint_state(FLAGS.log_root)
        except tf.errors.OutOfRangeError as e:
            tf.logging.error('Cannot restore checkpoint: %s', e)
            continue
        if not (ckpt_state and ckpt_state.model_checkpoint_path):
            tf.logging.info('No model to eval yet at %s', FLAGS.log_root)
            continue
        tf.logging.info('Loading checkpoint %s', ckpt_state.model_checkpoint_path)
        saver.restore(sess, ckpt_state.model_checkpoint_path)

        total_prediction, correct_prediction = 0, 0
        for i in range(EVAL_BATCH_COUNT):
            b = i * EVAL_BATCH_SIZE
            if i < (EVAL_BATCH_COUNT - 1) or (LAST_EVAL_BATCH_SIZE == 0):
                e = (i + 1) * EVAL_BATCH_SIZE
            else:
                e = i * EVAL_BATCH_SIZE + LAST_EVAL_BATCH_SIZE
            images, labels, _, _ = dt.fetch_batch_common(indices=range(b, e))
            (summaries, loss, predictions, truth, train_step) = sess.run(
                [model.summaries, model.cost, model.predictions, model.labels, model.global_step],
                feed_dict={images_ph: images, labels_ph: labels, is_training_ph: False})

            truth = np.argmax(truth, axis=1)
            predictions = np.argmax(predictions, axis=1)
            correct_prediction += np.sum(truth == predictions)
            total_prediction += predictions.shape[0]

        assert total_prediction == TEST_SET_SIZE, \
            'total_prediction equals %0d instead of %0d' %(total_prediction, TEST_SET_SIZE)
        precision = 1.0 * correct_prediction / total_prediction
        best_precision = max(precision, best_precision)

        precision_summ = tf.Summary()
        precision_summ.value.add(tag='Precision', simple_value=precision)
        summary_writer.add_summary(precision_summ, train_step)
        best_precision_summ = tf.Summary()
        best_precision_summ.value.add(tag='Best Precision', simple_value=best_precision)
        summary_writer.add_summary(best_precision_summ, train_step)
        summary_writer.add_summary(summaries, train_step)
        tf.logging.info('loss: %.4f, precision: %.4f, best precision: %.4f' %
                        (loss, precision, best_precision))
        summary_writer.flush()

        if FLAGS.eval_once:
          break

        time.sleep(60)

def print_params(hps):
    print ('Running script with these parameters:' , \
           'HPS:', \
           'hps.num_classes         = %0d'  % hps.num_classes, \
           'hps.lrn_rate            = %.8f' % hps.lrn_rate, \
           'hps.num_residual_units  = %0d'  % hps.num_residual_units, \
           'hps.xent_rate           = %.8f' % hps.xent_rate, \
           'hps.weight_decay_rate   = %.8f' % hps.weight_decay_rate, \
           'hps.relu_leakiness      = %.8f' % hps.relu_leakiness, \
           'hps.pool                = %0s'  % hps.pool, \
           'hps.optimizer           = %0s'  % hps.optimizer, \
           '', \
           'FLAGS:' , \
           'FLAGS.learning_rate     = %.8f' % FLAGS.learning_rate, \
           'FLAGS.dataset           = %0s'  % FLAGS.dataset, \
           'FLAGS.mode              = %0s'  % FLAGS.mode, \
           'FLAGS.train_data_dir    = %0s'  % FLAGS.train_data_dir, \
           'FLAGS.train_labels_file = %0s'  % FLAGS.train_labels_file, \
           'FLAGS.eval_data_dir     = %0s'  % FLAGS.eval_data_dir, \
           'FLAGS.eval_labels_file  = %0s'  % FLAGS.eval_labels_file, \
           'FLAGS.image_size        = %0d'  % FLAGS.image_size, \
           'FLAGS.eval_once         = %r'   % FLAGS.eval_once, \
           'FLAGS.log_root          = %0s'  % FLAGS.log_root, \
           'FLAGS.num_gpus          = %0d'  % FLAGS.num_gpus, \
           'FLAGS.learn_mode        = %0s'  % FLAGS.learn_mode, \
           'FLAGS.batch_size        = %0d'  % FLAGS.batch_size, \
           'FLAGS.clusters          = %0d'  % FLAGS.clusters, \
           'FLAGS.cap               = %0d'  % FLAGS.cap, \
           'FLAGS.active_epochs     = %0d'  % FLAGS.active_epochs, \
           '', \
           'Other parameters:', \
           'TRAIN_SET_SIZE          = %0d'  % TRAIN_SET_SIZE, \
           'TEST_SET_SIZE           = %0d'  % TEST_SET_SIZE, \
           'NUM_CLASSES             = %0d'  % NUM_CLASSES, \
           'TRAIN_BATCH_SIZE        = %0d'  % TRAIN_BATCH_SIZE, \
           'EVAL_BATCH_SIZE         = %0d'  % EVAL_BATCH_SIZE, \
           'TRAIN_BATCH_COUNT       = %0d'  % TRAIN_BATCH_COUNT, \
           'LAST_TRAIN_BATCH_SIZE   = %0d'  % LAST_TRAIN_BATCH_SIZE, \
           'EVAL_BATCH_COUNT        = %0d'  % EVAL_BATCH_COUNT, \
           'LAST_EVAL_BATCH_SIZE    = %0d'  % LAST_EVAL_BATCH_SIZE, \
           sep = '\n\t')

def main(_):
    if FLAGS.num_gpus == 0:
        dev = '/cpu:0'
    elif FLAGS.num_gpus == 1:
        dev = '/gpu:0'
    else:
        raise ValueError('Only support 0 or 1 gpu.')

    hps = resnet_model.HParams(num_classes=NUM_CLASSES,
                               lrn_rate=FLAGS.learning_rate,
                               num_residual_units=4, #was 5 in source code
                               xent_rate=1.0,
                               weight_decay_rate=0.000005, #was 0.0002
                               relu_leakiness=0.1,
                               pool='gap', #use gap or mp
                               optimizer='mom')

    print_params(hps)
    with tf.device(dev):
        if FLAGS.mode == 'train':
            train(hps)
        elif FLAGS.mode == 'eval':
            evaluate(hps)


if __name__ == '__main__':
    tf.logging.set_verbosity(tf.logging.INFO)
    tf.app.run()