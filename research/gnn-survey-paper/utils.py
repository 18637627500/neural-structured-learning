import os
import tensorflow as tf
import scipy.sparse as sp
import numpy as np

from models import GCN

def build_model(model_name, features_dim, num_layers, hidden_dim, num_classes, dropout):
    """Create gnn model and initialize parameters weights"""
    # Convert hidden_dim to integers
    for i in range(len(hidden_dim)):
        hidden_dim[i] = int(hidden_dim[i])

    # Only gcn available now
    if model_name == 'gcn':
        model = GCN(features_dim, num_layers, hidden_dim, num_classes, dropout)

    elif model_name == 'gat':
        raise NotImplementedError

    return model

def cal_acc(labels, logits):
    indices = tf.math.argmax(logits, axis=1)
    acc = tf.math.reduce_mean(tf.cast(indices == labels, dtype=tf.float32))
    return acc.numpy().item()

def encode_onehot(labels):
    # Provides a mapping from string labels to integer indices.
    label_index = {
        'Case_Based': 0,
        'Genetic_Algorithms': 1,
        'Neural_Networks': 2,
        'Probabilistic_Methods': 3,
        'Reinforcement_Learning': 4,
        'Rule_Learning': 5,
        'Theory': 6,
    }

    # Convert to onehot label
    num_classes = len(label_index)
    onehot_labels = np.zeros((len(labels), num_classes))
    idx = 0
    for s in labels:
        onehot_labels[idx, label_index[s]] = 1
        idx += 1
    return onehot_labels

def normalize_adj(adj):
    """Normalize adjacency matrix."""
    rowsum = np.array(adj.sum(1))
    d_inv_sqrt = np.power(rowsum, -0.5).flatten()
    d_mat_inv_sqrt = sp.diags(d_inv_sqrt)
    return adj.dot(d_mat_inv_sqrt).transpose().dot(d_mat_inv_sqrt).tocoo()

def normalize_features(features):
    """Row-normalize feature matrix."""
    rowsum = np.array(features.sum(1))
    r_inv = np.power(rowsum, -1).flatten()
    r_mat_inv = sp.diags(r_inv)
    features = r_mat_inv.dot(features)
    return features

def load_dataset(dataset):
    # Now only cora dataset available
    dir_path = os.path.join('data', dataset)
    content_path = os.path.join(dir_path, "{}.content".format(dataset))
    citation_path = os.path.join(dir_path, "{}.cites".format(dataset))

    content = np.genfromtxt(content_path, dtype=np.dtype(str))

    idx = np.array(content[:, 0], dtype=np.int32)
    features = sp.csr_matrix(content[:, 1:-1], dtype=np.float32)
    labels = encode_onehot(content[:, -1])

    # Dict which maps paper id to data id
    idx_map = {j: i for i, j in enumerate(idx)}
    edges_unordered = np.genfromtxt(citation_path, dtype=np.int32)
    edges = np.array(list(map(idx_map.get, edges_unordered.flatten())),
                     dtype=np.int32).reshape(edges_unordered.shape)
    adj = sp.coo_matrix((np.ones(edges.shape[0]), (edges[:, 0], edges[:, 1])),
                        shape=(labels.shape[0], labels.shape[0]),
                        dtype=np.float32)

    # build symmetric adjacency matrix
    adj = adj + adj.T.multiply(adj.T > adj) - adj.multiply(adj.T > adj)
    # Add self-connection edge
    adj = adj + sp.eye(adj.shape[0])

    features = normalize_features(features)
    adj = normalize_adj(adj)

    # 5% for train, 500 for validation, other for test
    train_num = int(labels.shape[0] * 0.05)
    val_num = train_num + 500

    features = tf.convert_to_tensor(np.array(features.todense()))
    labels = tf.convert_to_tensor(np.where(labels)[1])
    adj = tf.convert_to_tensor(np.array(adj.todense()))

    y_train = labels[:train_num]
    y_val = labels[train_num:val_num]
    y_test = labels[val_num:]
    return adj, features, y_train, y_val, y_test

