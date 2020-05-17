#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import math
import os
import osmnx as ox
import pandas as pd
import requests
import time

print('osmnx version', ox.__version__)


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

ox.config(use_cache=True,
          log_console=False,
          log_file=True,
          logs_folder=config['osmnx_log_path'],
          cache_folder=config['osmnx_cache_path'])

pause_duration = 0
urls_path = config['elevation_urls_path']
nodestoget_path = config['elevation_nodestoget_path']
elevations_path = config['elevation_elevations_path']

# set countries=None to get all
countries = None


# In[ ]:


# load nodes in order from file
# we will use this order to match the url batch requests in order back to their nodes
nodes = pd.read_csv(nodestoget_path, index_col='osmid')
print(ox.ts(), 'loaded', len(nodes), 'node osmids to get elevations for')


# In[ ]:


urls = pd.read_csv(urls_path, index_col='cluster')
print(ox.ts(), 'there are', len(urls), 'urls to get')
if len(urls) == 0:
	exit()

# make country and key cols
urls['country'] = urls.index.str.slice(0, 3)
urls['key'] = urls['url'].str.split('key=', expand=True)[1]


# In[ ]:


# if countries list exists, then only retain nodes/urls in those countries
if countries is not None:
    urls = urls[urls['country'].isin(countries)]
    nodes = nodes[nodes['cluster'].isin(urls.index)]
    print(ox.ts(), 'retained', len(nodes), 'nodes and', len(urls), 'urls for', countries)


# In[ ]:


# do a quick dry run to show what URLs we're pulling from preexisting cache vs requesting fresh from API
total_count_cached = 0
total_count_uncached = 0
groups = urls.groupby('key', sort=False)
for key, group in groups:

    count_cached = 0
    count_uncached = 0

    for url in group['url']:
        if ox.downloader._url_in_cache(url) is None:
            count_uncached += 1
        else:
            count_cached += 1

    print(ox.ts(), 'will get {} urls from cache and {} from API for key ~{}'.format(count_cached, count_uncached, key[-6:]))
    total_count_cached += count_cached
    total_count_uncached += count_uncached

print(ox.ts(), 'will get', total_count_cached, 'urls from cache and', total_count_uncached, 'from API in total')


# In[ ]:


def request_url(url, pause_duration=pause_duration):

    # check if this request is already in the cache (if ox.settings.use_cache=True)
    cached_response_json = ox.downloader._get_from_cache(url)
    if cached_response_json is not None:
        response_json = cached_response_json
        ox.log('Got node elevations from cache')
    else:
        try:
            # request the elevations from the API
            ox.log('Requesting node elevations from API: {}'.format(url))
            time.sleep(pause_duration)
            response = requests.get(url)
            assert response.ok
            response_json = response.json()
            ox.downloader._save_to_cache(url, response_json)
        except Exception as e:
            ox.log(e)
            print('Error - server responded with {}: {}'.format(response.status_code, response.reason))

    return response_json['results']


# In[ ]:


# for each country in the dataset, request each url
results = []
for country, group in urls.groupby('country'):
    print(ox.ts(), 'requesting', len(group), 'urls for', country)
    for url in group['url']:
        result = request_url(url)
        results.extend(result)


# In[ ]:


# check that all our vectors have the same number of elements
print(ox.ts(), 'we have', len(nodes), 'nodes and we got', len(results), 'elevations from the API')
assert len(results) == len(nodes)


# In[ ]:


# add elevation as an attribute to the nodes
nodes['elev'] = [result['elevation'] for result in results]
nodes['elev_res'] = [result['resolution'] for result in results]
nodes[['elev', 'elev_res']] = nodes[['elev', 'elev_res']].round(2) #round to centimeter
print(ox.ts(), 'attached', len(results), 'elevations to', len(nodes), 'node osmids')
results = None #release memory


# In[ ]:


# if any preexisting node elevation data, merge new data with it
if os.path.exists(elevations_path):

    # if elevations_path already exists, we downloaded some elevation data during a previous run
    preexisting_elevations = pd.read_csv(elevations_path).set_index('osmid').sort_index()
    print(ox.ts(), 'found {} nodes with preexisting elevation data'.format(len(preexisting_elevations)))

    # append the newly downloaded elevation data to these preexisting elevations
    elevs = preexisting_elevations.append(other=nodes, ignore_index=False, verify_integrity=False).sort_index()

    # remove any duplicates
    elevs = elevs.loc[~elevs.index.duplicated(keep='first')]
    assert elevs.index.is_unique
    print(ox.ts(), 'we now have {} nodes\' elevation data'.format(len(elevs)))

else:
    elevs = nodes
    print(ox.ts(), 'found no preexisting elevation data file')


# In[ ]:


# save (merged) node elevations to disk ONLY if we got data for all countries
# otherwise we just have the cached urls to hold results in the meantime
if countries is None:
    folder = elevations_path[:elevations_path.rfind('/')]
    if not os.path.exists(folder):
        os.makedirs(folder)
    elevs.to_csv(elevations_path, index=True, encoding='utf-8')
    print(ox.ts(), 'saved', len(elevs), 'node elevations to disk at', elevations_path)
else:
    print(ox.ts(), 'did not save node elevations to disk')


# In[ ]:




