from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import csv
import errno
import os
import re

import tensorflow as tf
from tensorboard.backend.event_processing import plugin_event_multiplexer as event_multiplexer  # pylint: disable=line-too-long
import tensorflow_TB.plots as plots
import json

# Control downsampling: how many scalar data do we keep for each run/tag
# combination?
SIZE_GUIDANCE = {'scalars': 1000}

def rm_str(str1, str2='_trainset'):
    """
    Removing str2 from str1
    :param str1: string
    :param str2: string
    :return: str1 without str2
    """
    return str1.replace(str2, '')

def extract_scalars(multiplexer, run, tag):
    """Extract tabular data from the scalars at a given run and tag.

    The result is a list of 3-tuples (wall_time, step, value).
    """
    tensor_events = multiplexer.Tensors(run, tag)
    return [(event.wall_time, event.step, tf.make_ndarray(event.tensor_proto).item()) for event in tensor_events]

def create_multiplexer(logdir):
    multiplexer = event_multiplexer.EventMultiplexer(tensor_size_guidance=SIZE_GUIDANCE)
    multiplexer.AddRunsFromDirectory(logdir)
    multiplexer.Reload()
    return multiplexer

def export_scalars(multiplexer, run, tag, filepath, write_headers=True):
    data = extract_scalars(multiplexer, run, tag)
    with open(filepath, 'w') as outfile:
        writer = csv.writer(outfile)
        if write_headers:
            writer.writerow(('wall_time', 'step', 'value'))
        for row in data:
            writer.writerow(row)

NON_ALPHABETIC = re.compile('[^A-Za-z0-9_]')

def munge_filename(name):
    """Remove characters that might not be safe in a filename."""
    return NON_ALPHABETIC.sub('_', name)

def mkdir_p(directory):
    try:
        os.makedirs(directory)
    except OSError as e:
        if not (e.errno == errno.EEXIST and os.path.isdir(directory)):
            raise

def main():
    logdirs = [
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111800',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111801',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111802',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111803',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111804',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111805',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111806',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111807',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111808',
        '/data/gilad/logs/multi_sf/cifar10/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111809',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111800',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111801',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111802',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111803',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111804',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111805',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111806',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111807',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111808',
        '/data/gilad/logs/multi_sf/cifar10/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111809',
        '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111800',
        '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111801',
        '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111802',
        '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111803',
        '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111804',
        '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111805',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111806',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111807',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111808',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111809',
        '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111800',
        '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111801',
        '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111802',
        '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111803',
        '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111804',
        '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111805',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111806',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111807',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111808',
        # '/data/gilad/logs/multi_sf/cifar100/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111809',
        '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111800',
        '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111801',
        '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111802',
        '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111803',
        # '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111804',
        # '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111805',
        # '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111806',
        # '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111807',
        # '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111808',
        # '/data/gilad/logs/multi_sf/mnist/small/log_no_multi_sf_lr_0.01-SUPERSEED=19111809',
        '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111800',
        '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111801',
        '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111802',
        '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111803',
        # '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111804',
        # '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111805',
        # '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111806',
        # '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111807',
        # '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111808',
        # '/data/gilad/logs/multi_sf/mnist/small/log_1_3_0.125_2_3_0.25_3_2_0.5_lr_0.01-SUPERSEED=19111809',
    ]

    run_names = ['test']

    # layers = ['input_images', 'init_conv',
    #           'unit_1_0', 'unit_1_1', 'unit_1_2', 'unit_1_3',
    #           'unit_2_0', 'unit_2_1', 'unit_2_2', 'unit_2_3',
    #           'unit_3_0', 'unit_3_1', 'unit_3_2', 'unit_3_3',
    #           'embedding_layer']

    # layers = ['input_images', 'conv1', 'pool1', 'conv2', 'pool2', 'embedding_layer']
    layers = []

    reg_tags = ['dnn_confidence_avg', 'dnn_confidence_median', 'dnn_score',
                'knn_confidence_avg', 'knn_confidence_median', 'knn_score', 'knn_kl_div_avg', 'knn_kl_div2_avg', 'knn_psame']
                # 'lr_confidence_avg' , 'lr_confidence_median' , 'lr_score' , 'lr_kl_div_avg' , 'lr_kl_div2_avg' , 'lr_psame',
                # 'svm_confidence_avg', 'svm_confidence_median', 'svm_score', 'svm_kl_div_avg', 'svm_kl_div2_avg', 'svm_psame']
    reg_tags += [s + '_trainset' for s in reg_tags]

    layer_tags = ['knn_confidence_avg', 'knn_confidence_median', 'knn_score',
                  'lr_confidence_avg' , 'lr_confidence_median' , 'lr_score' ,
                  'svm_confidence_avg', 'svm_confidence_median', 'svm_score',
                  'lr_knn_psame', 'svm_knn_psame', 'svm_lr_psame',
                  'lr_knn_kl_div_avg' , 'lr_knn_kl_div2_avg' , 'lr_knn_kl_div3_avg' , 'lr_knn_kl_div3_median' , 'lr_knn_kl_div4_avg' , 'lr_knn_kl_div4_median' ,
                  'svm_knn_kl_div_avg', 'svm_knn_kl_div2_avg', 'svm_knn_kl_div3_avg', 'svm_knn_kl_div3_median', 'svm_knn_kl_div4_avg', 'svm_knn_kl_div4_median',
                  'svm_lr_kl_div_avg' , 'svm_lr_kl_div2_avg' , 'svm_lr_kl_div3_avg' , 'svm_lr_kl_div3_median' , 'svm_lr_kl_div4_avg' , 'svm_lr_kl_div4_median']
    layer_tags += [s + '_trainset' for s in layer_tags]

    # tag_names = reg_tags
    # tag_names += [l+'/'+lt for l in layers for lt in layer_tags]

    for logdir in logdirs:
        output_dir = os.path.join(logdir, 'data_for_figures')
        mkdir_p(output_dir)
        print("Loading data for logdir: {}".format(logdir))
        multiplexer = create_multiplexer(logdir)
        for run_name in run_names:
            regular_dir = os.path.join(output_dir, 'regular')
            mkdir_p(regular_dir)
            for tag_name in reg_tags:
                output_filename = '%s___%s' % (munge_filename(run_name), munge_filename(tag_name))
                output_filepath = os.path.join(regular_dir, output_filename)
                print("Exporting (run=%r, tag=%r) to %r..." % (run_name, tag_name, output_filepath))
                export_scalars(multiplexer, run_name, tag_name, output_filepath)
            for layer in layers:
                layer_dir = os.path.join(output_dir, layer)
                mkdir_p(layer_dir)
                for layer_tag in layer_tags:
                    output_filename = '%s___%s' % (munge_filename(run_name), munge_filename(layer_tag))
                    output_filepath = os.path.join(layer_dir, output_filename)
                    print("Exporting (run=%r, layer=%r, tag=%r) to %r..." % (run_name, layer, layer_tag, output_filepath))
                    export_scalars(multiplexer, run_name, layer+'/'+layer_tag, output_filepath)
        print("Done extracting scalars. Now processing the JSON file")
        data = {}
        data['train']   = {}
        data['test']    = {}

        # build regular data
        data['train']['regular'] = {}
        data['test']['regular']  = {}
        for reg_tag in reg_tags:
            if 'trainset' in reg_tag:
                rec = 'train'
            else:
                rec = 'test'
            csv_file = os.path.join(regular_dir, 'test___' + reg_tag)
            data[rec]['regular'][rm_str(reg_tag)] = {}
            data[rec]['regular'][rm_str(reg_tag)]['steps'], data[rec]['regular'][rm_str(reg_tag)]['values'] = \
                plots.load_data_from_csv_wrapper(csv_file, mult=1.0, round_points=4)

        # build layer data
        data['train']['layer'] = {}
        data['test']['layer']  = {}
        for layer_tag in layer_tags:
            if 'trainset' in layer_tag:
                rec = 'train'
            else:
                rec = 'test'
            data[rec]['layer'][rm_str(layer_tag)] = []
            for layer in layers:
                csv_file = os.path.join(output_dir, layer, 'test___' + layer_tag)
                data[rec]['layer'][rm_str(layer_tag)].append(plots.load_data_from_csv_wrapper(csv_file, mult=1.0, round_points=4)[1][0])

        # export to JSON file
        json_file = os.path.join(output_dir, 'data.json')
        with open(json_file, 'w') as fp:
            json.dump(data, fp)

if __name__ == '__main__':
    main()
