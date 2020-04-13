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
output_gpkg_path = config['models_gpkg_path'] #where to save graph geopackages
output_graphml_path = config['models_graphml_path'] #where to save graphml files
output_nelist_path = config['models_nelist_path'] #where to save node/edge lists


# In[ ]:


def save_node_edge_lists(G, nelist_folder):
    
    # save node and edge lists as csv
    nodes, edges = ox.graph_to_gdfs(G, node_geometry=False, fill_edge_geometry=False)
    edges['length'] = edges['length'].round(3).astype(str)

    ecols = ['u', 'v', 'key', 'oneway', 'highway', 'name', 'length',
             'lanes', 'width', 'est_width', 'maxspeed', 'access', 'service',
             'bridge', 'tunnel', 'area', 'junction', 'osmid', 'ref']

    edges = edges.drop(columns=['geometry']).reindex(columns=ecols)
    nodes = nodes.reindex(columns=['osmid', 'x', 'y', 'ref', 'highway'])

    if not os.path.exists(nelist_folder):
        os.makedirs(nelist_folder)
    nodes.to_csv('{}/node_list.csv'.format(nelist_folder), index=False, encoding='utf-8')
    edges.to_csv('{}/edge_list.csv'.format(nelist_folder), index=False, encoding='utf-8')


# ## Load the prepped urban centers data

# In[ ]:


# load the prepped dataset
ucs = gpd.read_file(uc_gpkg_path).sort_values('B15', ascending=False)
print('loaded urban centers dataset with shape', ucs.shape)


# In[ ]:


# only retain urban centers marked as a "true positive" in quality control
ucs = ucs[ucs['QA2_1V'] == 1]
print('retained "true positive" urban centers dataset with shape', ucs.shape)


# In[ ]:


# only retain urban centers with at least 1 sq km of built-up area
ucs = ucs[ucs['B15'] >= 1]
print('retained >=1 km2 built-up area urban centers dataset with shape', ucs.shape)


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
print('begin getting', len(ucs_to_get), 'graphs')

for label, row in ucs_to_get.iterrows():
    try:
        # graph name = country + country iso + uc + uc id
        graph_name = '{}-{}-{}-{}'.format(row['CTR_MN_NM'], row['CTR_MN_ISO'], row['UC_NM_MN'], row['ID_HDC_G0'])
        
        graphml_folder = '{}/{}-{}'.format(output_graphml_path, row['CTR_MN_NM'], row['CTR_MN_ISO'])
        graphml_file = '{}-{}.graphml'.format(row['UC_NM_MN'], row['ID_HDC_G0'])
        
        gpkg_folder = '{}/{}-{}'.format(output_gpkg_path, row['CTR_MN_NM'], row['CTR_MN_ISO'])
        gpkg_file = '{}-{}.gpkg'.format(row['UC_NM_MN'], row['ID_HDC_G0'])
        
        nelist_folder = '{}/{}-{}/{}-{}'.format(output_nelist_path, row['CTR_MN_NM'], row['CTR_MN_ISO'], row['UC_NM_MN'], row['ID_HDC_G0'])        
        
        if not os.path.exists('{}/{}'.format(graphml_folder, graphml_file)):
            
            # timestamp and graph name
            print('{:%Y-%m-%d %H:%M:%S}'.format(datetime.datetime.now()), graph_name)
            
            # get graph
            G = ox.graph_from_polygon(polygon=row['geometry'].buffer(0),
                                      network_type=network_type,
                                      name=graph_name,
                                      retain_all=retain_all,
                                      simplify=simplify,
                                      truncate_by_edge=truncate_by_edge)
            
            # don't save graphs if they have fewer than 3 nodes
            if len(G.nodes()) > 2:
                save_node_edge_lists(G, nelist_folder)
                ox.save_graph_geopackage(G, folder=gpkg_folder, filename=gpkg_file)
                ox.save_graphml(G, folder=graphml_folder, filename=graphml_file)                
                count_success = count_success + 1
            else:
                count_small = count_small + 1
        else:
            count_already = count_already + 1
            
    except Exception as e:
        count_failed = count_failed + 1
        failed_list.append(graph_name)
        ox.log('"{}" failed: {}'.format(graph_name, e), level=lg.ERROR)


# In[ ]:


end_time = time.time() - start_time
print(f'{count_already} UCs already done')
print(f'{count_small} UCs too small')
print(f'{count_failed} UCs failed')
print(f'{count_success} UCs succeeded')
print('failed UCs:', str(failed_list))
print('Finished making {:,.0f} UC graphs in {:,.1f} seconds'.format(len(ucs_to_get), end_time))


# In[ ]:




