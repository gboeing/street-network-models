#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import networkx as nx
import os
import osmnx as ox
import pandas as pd

print('osmnx version', ox.__version__)

# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)
    
ox.config(log_file=True,
          logs_folder=config['osmnx_log_path'])

graphml_folder = config['models_graphml_path'] #where to load/save graphml
gpkg_folder = config['models_gpkg_path']       #where to save graph geopackages
nelist_folder = config['models_nelist_path']   #where to save node/edge lists
elevations_path = config['elevation_elevations_path']


# In[ ]:


def save_node_edge_lists(G, nelist_folder):
    
    # save node and edge lists as csv
    nodes, edges = ox.graph_to_gdfs(G, node_geometry=False, fill_edge_geometry=False)
    edges['length'] = edges['length'].round(2).astype(str)

    ecols = ['u', 'v', 'key', 'oneway', 'highway', 'name', 'length', 'grade', 'grade_abs',
             'lanes', 'width', 'est_width', 'maxspeed', 'access', 'service',
             'bridge', 'tunnel', 'area', 'junction', 'osmid', 'ref']

    edges = edges.drop(columns=['geometry']).reindex(columns=ecols)
    nodes = nodes.reindex(columns=['osmid', 'x', 'y', 'ref', 'highway'])

    if not os.path.exists(nelist_folder):
        os.makedirs(nelist_folder)
    nodes.to_csv('{}/node_list.csv'.format(nelist_folder), index=False, encoding='utf-8')
    edges.to_csv('{}/edge_list.csv'.format(nelist_folder), index=False, encoding='utf-8')


# In[ ]:


def graph_elevations(country_folder, graph_filename):
    
    # load graph
    graph_filepath = os.path.join(graphml_folder, country_folder, graph_filename)
    G = ox.load_graphml(filename=graph_filepath, folder='')
    print(ox.ts(), 'load', len(G.nodes()), 'nodes and', len(G.edges()), 'edges from', graph_filepath)
    
    # add elevation and elevation resolution as new attributes to edges
    graph_elevations = elevations.loc[set(G.nodes())].sort_index()
    nx.set_node_attributes(G, name='elevation', values=graph_elevations['elev'])
    nx.set_node_attributes(G, name='elevation_res', values=graph_elevations['elev_res'])
    
    # check if any graph node is missing elevation
    assert set(G.nodes()) == set(nx.get_node_attributes(G, 'elevation')) == set(nx.get_node_attributes(G, 'elevation_res'))

    # then calculate edge grades
    G = ox.add_edge_grades(G, add_absolute=True)
    
    # resave graphml now that it has elevations/grades
    graphml_output_folder = os.path.join(graphml_folder, country_folder)
    ox.save_graphml(G, filename=graph_filename, folder=graphml_output_folder)
    print(ox.ts(), 'save', graph_filepath)
    
    # save node/edge lists
    uc_name = graph_filename.replace('.graphml', '')
    nelist_output_folder = os.path.join(nelist_folder, country_folder, uc_name)
    save_node_edge_lists(G, nelist_output_folder)
    print(ox.ts(), 'save', nelist_output_folder)
    
    # save as geopackage
    gpkg_output_folder = os.path.join(gpkg_folder, country_folder)
    gpkg_filename = uc_name + '.gpkg'
    ox.save_graph_geopackage(G, folder=gpkg_output_folder, filename=gpkg_filename)
    print(ox.ts(), 'save', gpkg_output_folder + '/' + gpkg_filename)


# In[ ]:


elevations = pd.read_csv(elevations_path, usecols=['osmid', 'elev', 'elev_res']).set_index('osmid').sort_index()
print(ox.ts(), 'load elevation data for', len(elevations), 'nodes')


# In[ ]:


country_folders = sorted(os.listdir(graphml_folder))
for country_folder in country_folders:
    country_graphml_path = os.path.join(graphml_folder, country_folder)
    graphml_filenames = sorted(os.listdir(country_graphml_path))
    print(ox.ts(), 'process', len(graphml_filenames), 'graphs for', country_folder)
    for graphml_filename in graphml_filenames:
        graph_elevations(country_folder, graphml_filename)


# In[ ]:




