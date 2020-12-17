#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import datetime
import json
import multiprocessing as mp
import os
import osmnx as ox
import pandas as pd

print('osmnx version', ox.__version__)


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

ox.config(log_file=True, logs_folder=config['osmnx_log_path'])

if config['cpus'] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config['cpus']
print(ox.ts(), 'using', cpus, 'CPUs')

# In[ ]:


graphml_folder = config['models_graphml_path']
nodes_folder = config['elevation_country_nodes_path']


# In[ ]:


if not os.path.exists(nodes_folder):
    os.makedirs(nodes_folder)


# In[ ]:


country_folders = os.listdir(graphml_folder)
print('extracting nodes from UC graphs of {} countries'.format(len(country_folders)))


def get_graph_nodes(graphml_folder, country_folder, filename):
    filepath = os.path.join(graphml_folder, country_folder, filename)
    G = ox.load_graphml(filepath)
    graph_nodes = ox.graph_to_gdfs(G, edges=False, node_geometry=False)[['x', 'y']]
    return graph_nodes


for i, country_folder in enumerate(sorted(country_folders)):

    params = ((graphml_folder, country_folder, filename) for filename in os.listdir(os.path.join(graphml_folder, country_folder)))

    # create a pool of worker processes then map function/parameters to them
    pool = mp.Pool(cpus)
    sma = pool.starmap_async(get_graph_nodes, list(params))

    # get the results, close the pool, wait for worker processes to all exit
    results = sma.get()
    pool.close()
    pool.join()

    country_nodes = pd.DataFrame()
    for graph_nodes in results:
        country_nodes = country_nodes.append(graph_nodes, ignore_index=False, verify_integrity=False)

    # remove any duplicates
    country_nodes = country_nodes[~country_nodes.index.duplicated(keep='first')]

    # save to disk
    country_nodes = country_nodes.reset_index().rename(columns={'index':'osmid'})
    output_path = f'{nodes_folder}/{country_folder}.csv'
    country_nodes.to_csv(output_path, index=False, encoding='utf-8')

    ts = '{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now())
    print(i+1, ts, 'wrote {:,} nodes to {}'.format(len(country_nodes), output_path))


# In[ ]:


# how many total nodes did we end up with across all countries?
count = 0
for file in os.listdir(nodes_folder):
    count += len(pd.read_csv(os.path.join(nodes_folder, file)))
print('total node count across all countries:', count)

