"""
This module contains the TreePredictor class which is used for prediction.
"""
import numpy as np
from numba import njit, prange, jit
from multiprocessing import Process

PREDICTOR_RECORD_DTYPE = np.dtype([
    ('is_leaf', np.uint8),
    ('value', '50f8'),
    ('count', np.uint32),
    ('feature_idx', np.uint32),
    ('bin_threshold', np.uint8),
    ('threshold', np.float32),
    ('left', np.uint32),
    ('right', np.uint32),
    ('gain', np.float32),
    ('depth', np.uint32),
])

class TreePredictor:
    """Tree class used for predictions.

    Parameters
    ----------
    nodes : list of PREDICTOR_RECORD_DTYPE.
        The nodes of the tree.
    """
    def __init__(self, nodes, has_numerical_thresholds=True, prediction_dim=1):
        self.prediction_dim = prediction_dim
        self.nodes = nodes
        self.has_numerical_thresholds = has_numerical_thresholds
        out_type = str(prediction_dim) + 'f8'
        global PREDICTOR_RECORD_DTYPE
        PREDICTOR_RECORD_DTYPE = np.dtype([
            ('is_leaf', np.uint8),
            ('value', out_type),
            ('count', np.uint32),
            ('feature_idx', np.uint32),
            ('bin_threshold', np.uint8),
            ('threshold', np.float32),
            ('left', np.uint32),
            ('right', np.uint32),
            ('gain', np.float32),
            ('depth', np.uint32),
        ])

    def get_n_leaf_nodes(self):
        """Return number of leaves."""
        return int(self.nodes['is_leaf'].sum())

    def get_max_depth(self):
        """Return maximum depth among all leaves."""
        return int(self.nodes['depth'].max())

    def predict_binned(self, binned_data, out=None):
        """Predict raw values for binned data.

        Parameters
        ----------
        binned_data : array-like of np.uint8, shape=(n_samples, n_features)
            The binned input samples.
        out : array-like, shape=(n_samples,), optional (default=None)
            If not None, predictions will be written inplace in ``out``.

        Returns
        -------
        y : array, shape (n_samples,)
            The raw predicted values.
        """

        if binned_data.dtype != np.uint8:
            raise ValueError('binned_data dtype should be uint8')

        if out is None:
            out = np.empty((binned_data.shape[0], self.prediction_dim), dtype=np.float32)
        _predict_binned(self.nodes, binned_data, out)
        return out

    def predict(self, X):
        """Predict raw values for non-binned data.

        Parameters
        ----------
        X : array-like, shape=(n_samples, n_features)
            The input samples.

        Returns
        -------
        y : array, shape (n_samples,)
            The raw predicted values.
        """
        # TODO: introspect X to dispatch to numerical or categorical data
        # (dense or sparse) on a feature by feature basis.

        if not self.has_numerical_thresholds:
            raise ValueError(
                'This predictor does not have numerical thresholds so it can'
                'only predict pre-binned data.'
            )

        if X.dtype == np.uint8:
            raise ValueError(
                'X has uint8 dtype: use estimator.predict(X) if X is '
                'pre-binned, or convert X to a float32 dtype to be treated '
                'as numerical data'
            )

        out = np.empty((X.shape[0], self.prediction_dim), dtype=np.float32)
        _predict_from_numeric_data(self.nodes, X, out)
        return out


def _predict_one_binned(nodes, binned_data, out, idx):
    node = nodes[0]
    while True:
        if node['is_leaf']:
            out[idx] = node['value']
            return
        if binned_data[node['feature_idx']] <= node['bin_threshold']:
            node = nodes[node['left']]
        else:
            node = nodes[node['right']]


def _predict_binned(nodes, binned_data, out, thread=0, n_threads=1):
    processes = []
    for i in prange(binned_data.shape[0]):
        p = Process(target=_predict_one_binned, args=(nodes, binned_data[i], out, i))
        processes.append(p)
    for p in processes:
        p.start()
    for p in processes:
        p.join()


def _predict_one_from_numeric_data(nodes, numeric_data, out, idx):
    node = nodes[0]
    while True:
        if node['is_leaf']:
            out[idx] = node['value']
            return
        if numeric_data[node['feature_idx']] <= node['threshold']:
            node = nodes[node['left']]
        else:
            node = nodes[node['right']]


def _predict_from_numeric_data(nodes, numeric_data, out):
    processes = []
    print('multiprocessing')
    for i in prange(numeric_data.shape[0]):
        print(i)
        p = Process(target=_predict_one_from_numeric_data, args=(nodes, numeric_data[i], out, i))
        processes.append((i,p))
    for i,p in processes:
        print(i)
        p.start()
    for i,p in processes:

        print(i)
        p.join()

