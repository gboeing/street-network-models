#!/usr/bin/env python
# coding: utf-8

# In[ ]:

import datetime
import geopandas as gpd
import json
import logging as lg
import networkx as nx
import os
import osmnx as ox
import pandas as pd
import time

print('osmnx version', ox.__version__)
print('networkx version', nx.__version__)


# ## Config

# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)


# In[ ]:


ox.config(use_cache=True,
          log_file=True,
          log_console=False,
          logs_folder=config['osmnx_log_path'],
          cache_folder=config['osmnx_cache_path'])

# just cache the OSM data then interrupt before building graph model
ox.settings.cache_only_mode = True


# In[ ]:


network_type = 'drive'
retain_all = True
simplify = True
truncate_by_edge = True


# In[ ]:


uc_gpkg_path = config['uc_gpkg_path'] #prepped urban centers dataset


# save environment file
os.system('conda env export > ../environment.yml')
print(ox.ts(), 'exported conda env to ../environment.yml')


# ## Load the prepped urban centers data

# In[ ]:


# load the prepped dataset
ucs = gpd.read_file(uc_gpkg_path).sort_values('B15', ascending=False)
print(ox.ts(), 'loaded urban centers dataset with shape', ucs.shape)


# In[ ]:


# only retain urban centers marked as a "true positive" in quality control
ucs = ucs[ucs['QA2_1V'] == 1]
print(ox.ts(), 'retained "true positive" urban centers dataset with shape', ucs.shape)


# In[ ]:


# only retain urban centers with at least 1 sq km of built-up area
ucs = ucs[ucs['B15'] >= 1]
print(ox.ts(), 'retained >=1 km2 built-up area urban centers dataset with shape', ucs.shape)


# ## Download the urban centers' street networks one at a time

# In[ ]:


ucs_to_get = ucs#[ucs['ID_HDC_G0']==10]#.head(10)
start_time = time.time()


# In[ ]:
print(ox.ts(), 'begin getting', len(ucs_to_get), 'graphs')

for label, row in ucs_to_get.iterrows():

    graph_name = '{}-{}-{}-{}'.format(row['CTR_MN_NM'], row['CTR_MN_ISO'], row['UC_NM_MN'], row['ID_HDC_G0'])
    print(ox.ts(), graph_name)

    try:
        G = ox.graph_from_polygon(polygon=row['geometry'].buffer(0),
                                  network_type=network_type,
                                  retain_all=retain_all,
                                  simplify=simplify,
                                  truncate_by_edge=truncate_by_edge)
    except ox._errors.CacheOnlyModeInterrupt:
        # this happens every time because ox.settings.cache_only_mode = True
        pass

    except Exception as e:
        ox.log('"{}" failed: {}'.format(graph_name, e), level=lg.ERROR)
        print(e, graph_name)


# In[ ]:


end_time = time.time() - start_time
print(ox.ts(), 'Finished caching raw data for {:,.0f} graphs in {:,.1f} seconds'.format(len(ucs_to_get), end_time))


# In[ ]:




