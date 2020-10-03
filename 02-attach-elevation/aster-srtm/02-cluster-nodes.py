#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import math
import numpy as np
import os
import osmnx as ox
import pandas as pd
import string
from sklearn.cluster import KMeans


print('osmnx version', ox.__version__)


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

max_cluster_input_size = 90000
batch_size = 2000
nodes_folder = config['elevation_country_nodes_path']
clusters_folder = config['elevation_aster_nodeclusters_path']

if not os.path.exists(clusters_folder):
    os.makedirs(clusters_folder)


# # Helper Functions

# In[ ]:


def get_nodes(file):
    # load nodes from file
    nodes = pd.read_csv(os.path.join(nodes_folder, file), index_col='osmid')
    return nodes


# In[ ]:


def subcluster(nodes, labels, n=None, size=batch_size):

    if n is None:
        n = math.ceil(len(nodes.loc[labels]) / size)

    print(ox.ts(), 'clustering', len(nodes.loc[labels]), 'nodes into', n, 'clusters')
    X = nodes.loc[labels, ['x', 'y']].values
    kmeans = KMeans(n_clusters=n,
                    init='k-means++',
                    algorithm='full',
                    n_init=10,
                    max_iter=300,
                    random_state=0)

    kmeans = kmeans.fit(X)
    cluster_labels = pd.Series(kmeans.predict(X)).astype(str).values

    if 'cluster' in nodes.columns:
        # make this a subcluster
        separators = np.array(['-'] * len(cluster_labels))
        nodes.loc[labels, 'cluster'] = nodes.loc[labels, 'cluster'].str.cat(others=[separators, cluster_labels])
    else:
        # create a new cluster column
        nodes['cluster'] = cluster_labels


# In[ ]:


def longest_axis(points, x, y):

    x_range = points[x].max() - points[x].min()
    y_range = points[y].max() - points[y].min()
    if x_range > y_range:
        return x
    else:
        return y


def bissect_points(points, x='x', y='y'):

    axis = longest_axis(points, x, y)
    center = points[axis].median()
    half1 = points[points[axis] >= center].index
    half2 = points[points[axis] < center].index
    assert len(half1) + len(half2) == len(points)

    return half1, half2


# In[ ]:


# divide a cluster into halves
def bissect_cluster(nodes, group, size=batch_size):

    # spatially bissect the cluster's points
    subgroup0, subgroup1 = bissect_points(group)

    nodes.loc[subgroup0, 'cluster'] = nodes.loc[subgroup0, 'cluster'] + '-0'
    nodes.loc[subgroup1, 'cluster'] = nodes.loc[subgroup1, 'cluster'] + '-1'


# In[ ]:


def load_prep(filename):

    nodes = get_nodes(filename)
    print(ox.ts(), f'load {len(nodes)} total nodes')

    # remove any duplicate nodes that appeared in multiple graphs
    nodes = nodes.sort_index()
    nodes = nodes.loc[~nodes.index.duplicated(keep='first')]
    assert nodes.index.is_unique
    print(ox.ts(), 'keep {} unique nodes'.format(len(nodes)))

    return nodes


# In[ ]:


def cluster_nodes(nodes):

    # FIRST PASS
    # get the initial set of all country nodes into more manageably sized clusters
    # it's cpu/mem intensive to divide lots of points into lots of clusters
    # so this pass just divides lots of points into a few clusters
    if len(nodes) > max_cluster_input_size:
        subcluster(nodes, nodes.index, size=max_cluster_input_size*2)
    else:
        nodes['cluster'] = '0'


    # SECOND PASS
    # recursively subcluster the clusters to make the clusters small enough to
    # be able to cluster into lots of sub-sub-clusters of size batch_size
    while (nodes['cluster'].value_counts() > max_cluster_input_size).any():
        for cluster, group in nodes.groupby('cluster'):
            if len(group) > max_cluster_input_size:
                subcluster(nodes, group.index, size=max_cluster_input_size / 2)

    # THIRD PASS
    # now that the clusters are of digestible size, subcluster them down to
    # approximately the size of batch_size. kmeans produces uneven cluster sizes
    # so many will be bigger/smaller than batch_size... handle this in 4th pass
    for cluster, group in nodes.groupby('cluster'):
        if len(group) > batch_size:
            subcluster(nodes, group.index)

    # status check
    n_clusters = len(nodes['cluster'].unique())
    n_too_big = (nodes.groupby('cluster').size() > batch_size).sum()
    print(ox.ts(), 'we now have', n_clusters, 'clusters but', n_too_big, 'are too big and must be subdivided')

    # FOURTH PASS
    # if clustering produced clusters bigger than batch_size, bissect them
    while (nodes['cluster'].value_counts() > batch_size).any():
        for cluster, group in nodes.groupby('cluster'):
            if len(group) > batch_size:
                bissect_cluster(nodes, group)

    print(ox.ts(), 'all done, we now have', len(nodes['cluster'].unique()), 'clusters')
    return nodes


# In[ ]:


def check_and_save(nodes, filename):

    # add country code to cluster identifier
    country_code = filename.split('-')[1].split('.')[0]
    nodes['cluster'] = country_code + nodes['cluster']

    cluster_sizes = nodes.groupby('cluster').size()
    print(ox.ts(), 'largest cluster contains', cluster_sizes.max(), 'nodes and median is', int(cluster_sizes.median()))
    assert cluster_sizes.max() <= batch_size

    ideal_clusters = math.ceil(len(nodes) / batch_size)
    real_clusters = len(nodes['cluster'].unique())
    print(ox.ts(), 'ideally we\'d have', ideal_clusters, 'clusters but we have', real_clusters)

    output_filepath = os.path.join(clusters_folder, filename)
    nodes.to_csv(output_filepath, index=True, encoding='utf-8')
    print(ox.ts(), 'saved node clusters to disk at', output_filepath)


# # Run Process

# In[ ]:


for filename in sorted(os.listdir(nodes_folder)):

    print(ox.ts(), 'loading nodes from', filename)
    nodes = load_prep(filename)
    nodes = cluster_nodes(nodes)
    check_and_save(nodes, filename)

print(ox.ts(), 'process finished')


# In[ ]:




