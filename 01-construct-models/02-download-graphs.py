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


# In[ ]:


network_type = 'drive'
retain_all = True
simplify = True
truncate_by_edge = True


# In[ ]:


uc_gpkg_path = config['uc_gpkg_path'] #prepped urban centers dataset
output_graphml_path = config['models_graphml_path'] #where to save graphml files


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
count_failed = 0
count_success = 0
count_already = 0
count_small = 0
failed_list = []


# In[ ]:
print(ox.ts(), 'begin getting', len(ucs_to_get), 'graphs')

for label, row in ucs_to_get.iterrows():
    try:
        # graph name = country + country iso + uc + uc id
        graph_name = '{}-{}-{}-{}'.format(row['CTR_MN_NM'], row['CTR_MN_ISO'], row['UC_NM_MN'], row['ID_HDC_G0'])
        graphml_folder = '{}/{}-{}'.format(output_graphml_path, row['CTR_MN_NM'], row['CTR_MN_ISO'])
        graphml_file = '{}-{}.graphml'.format(row['UC_NM_MN'], row['ID_HDC_G0'])

        #gpkg_folder = '{}/{}-{}'.format(output_gpkg_path, row['CTR_MN_NM'], row['CTR_MN_ISO'])
        #gpkg_file = '{}-{}.gpkg'.format(row['UC_NM_MN'], row['ID_HDC_G0'])

        #nelist_folder = '{}/{}-{}/{}-{}'.format(output_nelist_path, row['CTR_MN_NM'], row['CTR_MN_ISO'], row['UC_NM_MN'], row['ID_HDC_G0'])

        filepath = os.path.join(graphml_folder, graphml_file)
        if not os.path.exists(filepath):

            # get graph
            print(ox.ts(), graph_name)
            G = ox.graph_from_polygon(polygon=row['geometry'].buffer(0),
                                      network_type=network_type,
                                      retain_all=retain_all,
                                      simplify=simplify,
                                      truncate_by_edge=truncate_by_edge)

            # don't save graphs if they have fewer than 3 nodes
            if len(G) > 2:
                #save_node_edge_lists(G, nelist_folder) #do this later when we've got the elevations too
                #ox.save_graph_geopackage(G, folder=gpkg_folder, filename=gpkg_file) #do this later when we've got the elevations too
                ox.save_graphml(G, filepath=filepath)
                count_success = count_success + 1
            else:
                count_small = count_small + 1
        else:
            count_already = count_already + 1

    except Exception as e:
        count_failed = count_failed + 1
        failed_list.append(graph_name)
        ox.log('"{}" failed: {}'.format(graph_name, e), level=lg.ERROR)
        print(e)


# In[ ]:


end_time = time.time() - start_time
print(ox.ts(), f'{count_already} UCs already done')
print(ox.ts(), f'{count_small} UCs too small')
print(ox.ts(), f'{count_failed} UCs failed')
print(ox.ts(), f'{count_success} UCs succeeded')
print(ox.ts(), 'failed UCs:', str(failed_list))
print(ox.ts(), 'Finished making {:,.0f} UC graphs in {:,.1f} seconds'.format(len(ucs_to_get), end_time))


# In[ ]:




