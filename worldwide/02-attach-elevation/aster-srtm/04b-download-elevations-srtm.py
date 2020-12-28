#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import math
import numpy as np
import os
import osmnx as ox
import pandas as pd
import requests
import time

print('osmnx version', ox.__version__)


# In[ ]:


# load configs
with open('../../config.json') as f:
    config = json.load(f)

ox.config(use_cache=True,
          log_console=False,
          log_file=True,
          logs_folder=config['osmnx_log_path'],
          cache_folder=config['osmnx_cache_path'])

pause_duration = 0

# to get srtm elevations, we can use the same urls and nodes as aster,
# but we'll change the endpoint in each url when requesting to get srtm instead
urls_path = config['elevation_aster_urls_path']
nodestoget_path = config['elevation_aster_nodestoget_path']
elevations_path = config['elevation_srtm_elevations_path']

# set countries=None to get all
countries = None #['AFG', 'ALB', 'ARM', 'BHS', 'BRB', 'BLR', 'BLZ', 'BIH', 'BWA']


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

# change endpoint from aster to srtm3
urls['url'] = urls['url'].str.replace('astergdemJSON', 'srtm3JSON')

# make country and key cols
urls['country'] = urls.index.str.slice(0, 3)


# In[ ]:


# if countries list exists, then only retain nodes/urls in those countries
if countries is not None:
    urls = urls[urls['country'].isin(countries)]
    nodes = nodes[nodes['cluster'].isin(urls.index)]
    print(ox.ts(), 'retained', len(nodes), 'nodes and', len(urls), 'urls for', countries)


# In[ ]:


# do a quick dry run to show what URLs we're pulling from preexisting cache vs requesting fresh from API
count_cached = 0
count_uncached = 0
for url in urls['url']:
    if ox.downloader._url_in_cache(url) is None:
        count_uncached += 1
    else:
        count_cached += 1

print(ox.ts(), 'will get', count_cached, 'urls from cache and', count_uncached, 'from API')

# In[ ]:


def request_url(url, pause_duration=pause_duration):

    # check if this request is already in the cache (if ox.settings.use_cache=True)
    cached_response_json = ox.downloader._retrieve_from_cache(url)
    if cached_response_json is not None:
        response_json = cached_response_json
        ox.log('Got node elevations from cache')
    else:
        try:
            # request the elevations from the API
            ox.log('Requesting node elevations from API: {}'.format(url))
            time.sleep(pause_duration)

            # convert GET to POST to work around apache url length limits
            params = dict()
            endpoint, url_params = url.split('?')
            for chunk in url_params.split('&'):
                key, value = chunk.split('=')
                params[key] = value

            response = requests.post(endpoint, data=params, timeout=120)
            assert response.ok
            response_json = response.json()
            assert 'geonames' in response_json
            ox.downloader._save_to_cache(url, response_json, response.status_code)

        except Exception as e:
            ox.log(e)
            print(e)
            print('Error - server responded with {}: {}. {}'.format(response.status_code, response.reason, response.text))

    return response_json


# In[ ]:


# for each country in the dataset, request each url
credits = []
tiles = []
positions = []
results = []
for country, group in urls.groupby('country'):
    print(ox.ts(), 'requesting', len(group), 'urls for', country)
    for url in group['url']:
        response_json = request_url(url)
        credits.append(float(response_json['credits']))
        tiles.append(int(response_json['numDistinctTiles']))
        positions.append(int(response_json['numDistinctPositions']))
        result = [result['srtm3'] for result in response_json['geonames']]
        results.extend(result)

print(ox.ts(), 'credits:', round(sum(credits), 2), 'tiles:', sum(tiles), 'distinct positions:', sum(positions))

# In[ ]:


# check that all our vectors have the same number of elements
print(ox.ts(), 'we have', len(nodes), 'nodes and we got', len(results), 'elevations from the API')
assert len(results) == len(nodes)


# In[ ]:


# add elevation as an attribute to the node IDs, replace nulls (-32768) with nan
nodes['elev'] = results
nodes['elev'] = nodes['elev'].replace(-32768, np.nan)

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



