#!/usr/bin/env python
# coding: utf-8

#

# In[ ]:


import json
import os
import osmnx as ox
import pandas as pd

print('osmnx version', ox.__version__)


# In[ ]:

# load google maps elevation api keys
with open('keys.json') as f:
    data = json.load(f)
    username = data['username']

# load configs
with open('../../config.json') as f:
    config = json.load(f)

batch_size = 2000

# input data
nodes_folder = config['elevation_aster_nodeclusters_path'] #clustered nodes with xy data
elevations_path = config['elevation_aster_elevations_path'] #any preexisting elevations data from previous runs

# output data
urls_path = config['elevation_aster_urls_path'] #urls we create
nodestoget_path = config['elevation_aster_nodestoget_path'] #node osmids in same order as their coords appear in batched lists of urls


# In[ ]:


def get_url(cluster, username=username):
    # google maps elevation API endpoint
    url_template = 'http://ws.geonames.net/astergdemJSON?lats={}&lngs={}&username={}'
    lats = ','.join(cluster['lat'])
    lngs = ','.join(cluster['lng'])
    return url_template.format(lats, lngs, username)


# In[ ]:


def get_nodes(file):
    # load clustered nodes from file
    nodes = pd.read_csv(f'{nodes_folder}/{file}', index_col='osmid')

    # create lat and lng columns rounded to 5 decimals (ie, 1-meter precision)
    nodes['lat'] = nodes['y'].map(lambda y: '{:.5f}'.format(y))
    nodes['lng'] = nodes['x'].map(lambda x: '{:.5f}'.format(x))
    return nodes.drop(columns=['x', 'y'])


# In[ ]:


print(ox.ts(), 'loading nodes from files:', end=' ')

# load clustered nodes
nodes = pd.DataFrame()
for file in sorted(os.listdir(nodes_folder)):
    print(file.split('-')[0], end=' ', flush=True)
    nodes = nodes.append(other=get_nodes(file), ignore_index=False, verify_integrity=False)

print('')
print(ox.ts(), f'load {len(nodes)} total nodes')


# In[ ]:


# remove any duplicate nodes that appeared in multiple graphs
nodes = nodes.sort_index()
nodes = nodes.loc[~nodes.index.duplicated(keep='first')]
assert nodes.index.is_unique
print(ox.ts(), 'keep {} unique nodes'.format(len(nodes)))


# In[ ]:


# if this file already exists, we have already downloaded some elevation data
# so drop any nodes that we already downloaded elevation for
if os.path.exists(elevations_path):
    preexisting = pd.read_csv(elevations_path).set_index('osmid')
    existing_elevations = preexisting[pd.notnull(preexisting['elev'])]
    print(ox.ts(), 'found', len(existing_elevations), 'preexisting node elevations at', elevations_path)
    labels = existing_elevations.reindex(nodes.index).dropna().index
    nodes = nodes.drop(labels=labels)
print(ox.ts(), 'retained {} nodes we currently lack elevation data for'.format(len(nodes)))


# In[ ]:

# resort by cluster so nodes and urls will be in same order
nodes = nodes.sort_values('cluster')
clusters = nodes.groupby('cluster', sort=True)
print(ox.ts(), 'there are {} clusters'.format(len(clusters)))


# create one url for each cluster of nodes
urls = {label:get_url(cluster) for label, cluster in clusters}
urls = pd.Series(urls)
assert len(nodes['cluster'].unique()) == len(urls)
print(ox.ts(), 'constructed {} urls'.format(len(urls)))



# In[ ]:


# save urls to disk
urls = urls.rename('url')
urls.index.rename('cluster', inplace=True)
urls.to_csv(urls_path, index=True, encoding='utf-8')
print(ox.ts(), 'saved {} urls at {}'.format(len(urls), urls_path))


# In[ ]:


# save nodes that we are going to request elevations for to disk in order
# we will use this order to match the url batch requests back to their nodes
nodes.to_csv(nodestoget_path, index=True, encoding='utf-8')
print(ox.ts(), 'saved {} node osmids at {}'.format(len(nodes), nodestoget_path))


# In[ ]:




