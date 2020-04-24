#!/usr/bin/env python
# coding: utf-8

# each api key belongs to a project attached to a different billing account. each billing account gets $200/month credit.
# 
# from: https://cloud.google.com/maps-platform/pricing/sheet/
# 
# up to 40,000 calls for free monthly
# 
# From https://developers.google.com/maps/documentation/elevation/intro
# 
# > URLs must be properly encoded to be valid and are limited to 8192 characters for all web services. Be aware of this limit when constructing your URLs. Note that different browsers, proxies, and servers may have different URL character limits as well.

# In[ ]:


import json
import os
import osmnx as ox
import pandas as pd
from keys import api_keys

print('osmnx version', ox.__version__)


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

batch_size = 400
max_url_length = 8192
max_requests = 39000

# input data
nodes_folder = config['elevation_nodeclusters_path'] #clustered nodes with xy data
elevations_path = config['elevation_elevations_path'] #any preexisting elevations data from previous runs

# output data
urls_path = config['elevation_urls_path'] #urls we create
nodestoget_path = config['elevation_nodestoget_path'] #node osmids in same order as their coords appear in batched lists of urls


# In[ ]:


def get_url(cluster):
    # google maps elevation API endpoint
    url_template = 'https://maps.googleapis.com/maps/api/elevation/json?locations={}&key='
    locations = '|'.join(cluster['latlng'])
    return url_template.format(locations)


# In[ ]:


def get_nodes(file):
    # load nodes from file
    nodes = pd.read_csv(f'{nodes_folder}/{file}', index_col='osmid')
    
    # create latlng column rounded to 5 decimals (ie, 1-meter precision)
    nodes['latlng'] = nodes.apply(lambda row: '{:.5f},{:.5f}'.format(row['y'], row['x']), axis=1)
    
    return nodes.drop(columns=['x', 'y'])


# In[ ]:


print(ox.ts(), 'loading nodes from graph files:', end=' ')

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
    existing_elevations = preexisting[pd.notnull(preexisting['elevation'])]
    labels = existing_elevations.reindex(nodes.index).index
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
print(ox.ts(), 'constructed {} urls'.format(len(urls)))


# In[ ]:


keys_list = []
for key in api_keys:
    keys_list.extend([key] * max_requests)

keys = pd.Series(data=keys_list[0:len(urls)], index=urls.index)
assert len(keys) == len(urls)

urls = urls + keys


# In[ ]:


# ensure that all urls are less than the max allowed length
assert (urls.map(len) < max_url_length).all()
assert len(nodes['cluster'].unique()) == len(urls)


# In[ ]:


# save urls to disk
urls = urls.rename('url')
urls.index.rename('cluster', inplace=True)
urls.to_csv(urls_path, index=True, encoding='utf-8')
print(ox.ts(), 'saved {} urls at {}'.format(len(urls), urls_path))


# In[ ]:


key_counts = keys.value_counts().reindex(api_keys)
for key, count in key_counts.iteritems():
    print(ox.ts(), 'key ~{} has {} urls'.format(key[-6:], count))


# In[ ]:


# save nodes that we are going to request elevations for to disk in order
# we will use this order to match the url batch requests back to their nodes
nodes.to_csv(nodestoget_path, index=True, encoding='utf-8')
print(ox.ts(), 'saved {} node osmids at {}'.format(len(nodes), nodestoget_path))


# In[ ]:




