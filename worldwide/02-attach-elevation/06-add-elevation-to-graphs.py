#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import multiprocessing as mp
import networkx as nx
import os
import osmnx as ox
import pandas as pd
import random

print('osmnx version', ox.__version__)

# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

ox.config(log_file=True,
          logs_folder=config['osmnx_log_path'])

if config['cpus'] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config['cpus']
print(ox.ts(), 'using', cpus, 'CPUs')

graphml_folder = config['models_graphml_path'] #where to load/save graphml
gpkg_folder = config['models_gpkg_path']       #where to save graph geopackages
nelist_folder = config['models_nelist_path']   #where to save node/edge lists
elevations_input_path = config['elevation_final_path']

# load elevations data as global df
df_elevs = pd.read_csv(elevations_input_path).set_index('osmid').sort_index()
print(ox.ts(), 'loaded elevation data for', len(df_elevs), 'nodes')


# In[ ]:


def save_node_edge_lists(G, nelist_folder):

    # save node and edge lists as csv
    nodes, edges = ox.graph_to_gdfs(G, node_geometry=False, fill_edge_geometry=False)

    edges[['grade', 'grade_abs', 'length']] = edges[['grade', 'grade_abs', 'length']].round(3)
    ecols = ['u', 'v', 'key', 'oneway', 'highway', 'name', 'length', 'grade', 'grade_abs',
             'lanes', 'width', 'est_width', 'maxspeed', 'access', 'service',
             'bridge', 'tunnel', 'area', 'junction', 'osmid', 'ref']
    edges = edges.drop(columns=['geometry']).reset_index().reindex(columns=ecols)

    ncols = ['osmid', 'x', 'y', 'elevation', 'elevation_aster', 'elevation_srtm', 'ref', 'highway']
    nodes = nodes.reset_index().reindex(columns=ncols)

    if not os.path.exists(nelist_folder):
        os.makedirs(nelist_folder)
    nodes.to_csv(os.path.join(nelist_folder, 'node_list.csv'), index=False, encoding='utf-8')
    edges.to_csv(os.path.join(nelist_folder, 'edge_list.csv'), index=False, encoding='utf-8')


# In[ ]:


def add_elevations(country_folder, graph_filename):

    # load graph
    graph_filepath = os.path.join(graphml_folder, country_folder, graph_filename)
    G = ox.load_graphml(filepath=graph_filepath)
    print(ox.ts(), 'load', len(G), 'nodes and', len(G.edges), 'edges from', graph_filepath)

    # get the elevation data for this graph's nodes
    graph_elevs = df_elevs.loc[set(G.nodes)].sort_index()

    # set nodes' elevation attributes
    nx.set_node_attributes(G, name='elevation', values=graph_elevs['elevation'].astype(int))
    nx.set_node_attributes(G, name='elevation_aster', values=graph_elevs['elev_aster'].dropna().astype(int))
    nx.set_node_attributes(G, name='elevation_srtm', values=graph_elevs['elev_srtm'].dropna().astype(int))

    # confirm that no graph node is missing elevation
    assert set(G.nodes) == set(nx.get_node_attributes(G, 'elevation'))

    # then calculate edge grades
    G = ox.add_edge_grades(G, add_absolute=True)

    # resave graphml now that it has elevations/grades
    ox.save_graphml(G, filepath=graph_filepath)
    print(ox.ts(), 'save', graph_filepath)

    # save node/edge lists
    uc_name = graph_filename.replace('.graphml', '')
    nelist_output_folder = os.path.join(nelist_folder, country_folder, uc_name)
    save_node_edge_lists(G, nelist_output_folder)
    print(ox.ts(), 'save', nelist_output_folder)

    # save as geopackage
    gpkg_filename = uc_name + '.gpkg'
    gpkg_filepath = os.path.join(gpkg_folder, country_folder, gpkg_filename)
    ox.save_graph_geopackage(G, filepath=gpkg_filepath)
    print(ox.ts(), 'save', gpkg_filepath)


# In[ ]:

params = []
country_folders = sorted(os.listdir(graphml_folder))
for country_folder in country_folders:
    country_graphml_path = os.path.join(graphml_folder, country_folder)
    graphml_filenames = sorted(os.listdir(country_graphml_path))
    for graphml_filename in graphml_filenames:
        params.append((country_folder, graphml_filename))

# randomly order params so one thread doesn't have to do all the big graphs
random.shuffle(params)
print(ox.ts(), 'add node elevations to', len(params), 'graphs files')

# create a pool of worker processes then map function/parameters to them
pool = mp.Pool(cpus)
sma = pool.starmap_async(add_elevations, params)

# get the results, close the pool, wait for worker processes to all exit
results = sma.get()
pool.close()
pool.join()

print(ox.ts(), 'process finished')
