import os
import sys

cwd = os.getcwd() # tensorflow-TB
sys.path.insert(0, cwd)

import lib.logger.logger as logger
from lib.logger.logging_config import logging_config
from utils.parameters import Parameters
from utils.factories import Factories
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from lib.active_kmean import KMeansWrapper
from sklearn.datasets import make_blobs


logging = logging_config()

logging.disable(logging.DEBUG)
log = logger.get_logger('main')

prm_file = '/data/gilad/logs/log_2210_220817_wrn-fc2_kmeans_SGD_init_200_clusters_4_cap_204/parameters.ini'

prm = Parameters()
prm.override(prm_file)

dev = prm.network.DEVICE

factories = Factories(prm)

model = factories.get_model()
model.print_stats()  # debug

preprocessor = factories.get_preprocessor()
preprocessor.print_stats()  # debug

train_dataset = factories.get_train_dataset(preprocessor)
validation_dataset = factories.get_validation_dataset(preprocessor)

dataset_wrapper = DatasetWrapper(prm.dataset.DATASET_NAME + '_wrapper', prm, train_dataset, validation_dataset)
dataset_wrapper.print_stats()

# trainer = factories.get_trainer(model, dataset_wrapper)
# trainer.print_stats()  # debug

# start debugging
# setting up variables around (10,10), (-10,10), (10,-10), (-10,-10)

n_samples = 1500
random_state = 10
X, y = make_blobs(n_samples=n_samples, random_state=random_state, centers=4, cluster_std=0.5)
plt.scatter(X[:, 0], X[:, 1], c=y)

# set fixed centers in: [0.25, -6] and [-5.5, 5.5]
fixed_centers = np.array([[0.25, -6], [-5.5, 5.5]])

# construct k-mean object:
KM = KMeansWrapper(name='KMeansWrapper', prm=prm,
                   fixed_centers=fixed_centers,
                   n_clusters=4,
                   random_state=random_state)
centers = KM.fit_predict_centers(X)
y_pred = KM.labels_
plt.figure(2)
plt.scatter(X[:, 0], X[:, 1], c=y_pred)







