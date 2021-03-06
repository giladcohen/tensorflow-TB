from __future__ import division

import tensorflow_TB.lib.logger.logger as logger
import tensorflow_TB.lib.trainers.active_learning.active_learning_select_functions as alf

from tensorflow_TB.lib.datasets.active_dataset_wrapper import ActiveDatasetWrapper
from tensorflow_TB.lib.datasets.dataset_wrapper import DatasetWrapper
from tensorflow_TB.lib.datasets.random_dataset_wrapper import RandomDatasetWrapper
from tensorflow_TB.lib.datasets.semi_supervised_dataset_wrapper import SemiSupervisedDatasetWrapper
from tensorflow_TB.lib.datasets.mnist_1v7 import MNIST_1V7
from tensorflow_TB.lib.datasets.cifar10_cats_v_dogs import CIFAR10_CatsVDogs
from tensorflow_TB.lib.datasets.cifar10_cars_vs_trucks import CIFAR10_CarsVTrucks
from tensorflow_TB.lib.datasets.cifar10_airplanes_vs_ships import CIFAR10_AirplanesVShips

from tensorflow_TB.lib.models.dml_resnet_model import DMLResNet
from tensorflow_TB.lib.models.resnet_model import ResNet
from tensorflow_TB.lib.models.resnet_multi_sf_model import ResnetMultiSf
from tensorflow_TB.lib.models.lenet_model import LeNet
from tensorflow_TB.lib.models.fc2_model import FC2Net

from tensorflow_TB.lib.testers.ensemble_tester import EnsembleTester
from tensorflow_TB.lib.testers.knn_classifier_tester import KNNClassifierTester
from tensorflow_TB.lib.testers.multi_layer_knn_classifier_tester import MultiLayerKNNClassifierTester
from tensorflow_TB.lib.testers.multi_knn_classifier_tester import MultiKNNClassifierTester
from tensorflow_TB.lib.testers.bayesian_multi_knn_classifier_tester import BayesianMultiKNNClassifierTester
from tensorflow_TB.lib.testers.knn_influence_tester import KNNInfluenceTester
from tensorflow_TB.lib.testers.lr_retrain_tester import LRRetrain

from tensorflow_TB.lib.trainers.active_trainer import ActiveTrainer
from tensorflow_TB.lib.trainers.classification_ma_trainer import ClassificationMATrainer
from tensorflow_TB.lib.trainers.classification_metrics_trainer import ClassificationMetricsTrainer
from tensorflow_TB.lib.trainers.classification_trainer import ClassificationTrainer
from tensorflow_TB.lib.trainers.dml_classification_trainer import DMLClassificationTrainer
from tensorflow_TB.lib.trainers.dynamic_model_trainer import DynamicModelTrainer
from tensorflow_TB.lib.trainers.hooks.decay_by_score_setter import DecayByScoreSetter
from tensorflow_TB.lib.trainers.hooks.fixed_schedule_setter import FixedScheduleSetter
from tensorflow_TB.lib.trainers.hooks.learning_rate_setter_base import LearningRateSetterBase
from tensorflow_TB.lib.trainers.semi_supervised_trainer import SemiSupervisedTrainer


class Factories(object):
    """Class which encapsulate all factories in the TB"""

    def __init__(self, prm):
        self.log = logger.get_logger('factories')
        self.prm = prm

        self.dataset_name               = self.prm.dataset.DATASET_NAME
        self.trainer                    = self.prm.train.train_control.TRAINER
        self.architecture               = self.prm.network.ARCHITECTURE
        self.learning_rate_setter       = self.prm.train.train_control.learning_rate_setter.LEARNING_RATE_SETTER
        self.tester                     = self.prm.test.test_control.TESTER
        self.active_selection_criterion = self.prm.train.train_control.ACTIVE_SELECTION_CRITERION

    def get_dataset(self):
        available_datasets = {'cifar10'                  : DatasetWrapper,
                              'cifar10_cats_v_dogs'      : CIFAR10_CatsVDogs,
                              'cifar10_cars_v_trucks'    : CIFAR10_CarsVTrucks,
                              'cifar10_airplanes_v_ships': CIFAR10_AirplanesVShips,
                              'cifar100'                 : DatasetWrapper,
                              'mnist'                    : DatasetWrapper,
                              'mnist_1v7'                : MNIST_1V7,
                              'active_cifar10'           : ActiveDatasetWrapper,
                              'active_cifar100'          : ActiveDatasetWrapper,
                              'semi_cifar10'             : SemiSupervisedDatasetWrapper,
                              'semi_cifar100'            : SemiSupervisedDatasetWrapper,
                              'random_cifar10'           : RandomDatasetWrapper,
                              'random_cifar100'          : RandomDatasetWrapper,
                              'random_mnist'             : RandomDatasetWrapper}
        if self.dataset_name in available_datasets:
            dataset = available_datasets[self.dataset_name](self.dataset_name + '_dataset_wrapper', self.prm)
            return dataset
        else:
            err_str = 'get_dataset: dataset {} was not found. Available datasets are: {}'.format(self.dataset_name, available_datasets.keys())
            self.log.error(err_str)
            raise AssertionError(err_str)

    def get_model(self):
        available_networks = {'Wide-Resnet-28-10'               : ResNet,
                              'Wide-Resnet-28-10_MultiSf'       : ResnetMultiSf,
                              'DML-Wide-Resnet-28-10'           : DMLResNet,
                              'LeNet'                           : LeNet,
                              'FC2Net'                          : FC2Net}
        if self.architecture in available_networks:
            model = available_networks[self.architecture](self.architecture, self.prm)
            self.log.info('get_model: returning ' + str(model))
            return model
        else:
            err_str = 'get_model: model {} was not found. Available models are: {}'.format(self.architecture, available_networks.keys())
            self.log.error(err_str)
            raise AssertionError(err_str)

    def get_trainer(self, model, dataset):
        available_trainers = {'simple'                               : ClassificationTrainer,
                              'simple_ma'                            : ClassificationMATrainer,
                              'simple_metrics'                       : ClassificationMetricsTrainer,
                              'dml'                                  : DMLClassificationTrainer,
                              'active'                               : ActiveTrainer,
                              'active_dynamic'                       : DynamicModelTrainer,
                              'semi_supervised'                      : SemiSupervisedTrainer}
        if self.trainer in available_trainers:
            trainer = available_trainers[self.trainer](self.trainer, self.prm, model, dataset)
            self.log.info('get_trainer: returning ' + str(trainer))
            trainer.build()
            return trainer
        else:
            err_str = 'get_trainer: trainer {} was not found. Available trainers are: {}'.format(self.trainer, available_trainers.keys())
            self.log.error(err_str)
            raise AssertionError(err_str)

    def get_tester(self, model, dataset):
        available_testers = {'knn_classifier'                       : KNNClassifierTester,
                             'multi_layer_knn_classifier'           : MultiLayerKNNClassifierTester,
                             'ensemble_classifier'                  : EnsembleTester,
                             'multi_knn_classifier'                 : MultiKNNClassifierTester,
                             'bayesian_multi_knn_classifier_tester' : BayesianMultiKNNClassifierTester,
                             'knn_influence'                        : KNNInfluenceTester,
                             'lr_retrain'                           : LRRetrain}
        if self.tester in available_testers:
            tester = available_testers[self.tester](self.tester, self.prm, model, dataset)
            self.log.info('get_tester: returning ' + str(tester))
            tester.build()
            return tester
        else:
            err_str = 'get_tester: tester {} was not found. Available testers are: {}'.format(self.tester, available_testers.keys())
            self.log.error(err_str)
            raise AssertionError(err_str)

    def get_learning_rate_setter(self, model, retention):
        available_setters = {'fixed': LearningRateSetterBase,
                             'fixed_schedule': FixedScheduleSetter,
                             'decay_by_score': DecayByScoreSetter}
        if self.learning_rate_setter in available_setters:
            setter = available_setters[self.learning_rate_setter](self.learning_rate_setter, self.prm, model, retention)
            self.log.info('get_learning_rate_setter: returning ' + str(setter))
            return setter
        else:
            err_str = 'get_learning_rate_setter: learning_rate_setter {} was not found. Available setters are: {}'.format(self.learning_rate_setter, available_setters.keys())
            self.log.error(err_str)
            raise AssertionError(err_str)

    def get_active_selection_fn(self):
        available_functions = {'random_sampler'                     : alf.random_sampler,
                               'most_uncertained_dnn'               : alf.most_uncertained_dnn,
                               'most_uncertained_knn'               : alf.most_uncertained_knn,
                               'min_mul_dnn_max_knn_same'           : alf.min_mul_dnn_max_knn_same,
                               'most_uncertained_following_min_corr': alf.most_uncertained_following_min_corr,
                               'min_corr_following_most_uncertained': alf.min_corr_following_most_uncertained}
        if self.active_selection_criterion in available_functions:
            function = available_functions[self.active_selection_criterion]
            self.log.info('get_active_selection_fn: returning ' + self.active_selection_criterion)
            return function
        else:
            err_str = 'get_active_selection_fn: active_selection_criterion {} was not found. Available functions are: {}'.format(self.active_selection_criterion, available_functions.keys())
            self.log.error(err_str)
            raise AssertionError(err_str)

