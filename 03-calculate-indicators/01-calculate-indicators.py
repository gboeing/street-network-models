#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import networkx as nx
import numpy as np
import os
import osmnx as ox
import pandas as pd
from scipy import stats

print('osmnx version', ox.__version__)
print('networkx version', nx.__version__)


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)
    
ox.config(log_file=True,
          logs_folder=config['osmnx_log_path'])

graphml_folder = config['models_graphml_path'] #where to load graphml files
indicators_path = config['indicators_path']    #where to save output indicators
save_every_n = 100 #save results every n cities

indicators_folder = indicators_path[:indicators_path.rfind('/')]
if not os.path.exists(indicators_folder):
    os.makedirs(indicators_folder)

clean_int_tol = 10 #meters for intersection cleaning tolerance
    
entropy_bins = 36
min_entropy_bins = 4 #perfect grid
perfect_grid = [1] * min_entropy_bins + [0] * (entropy_bins - min_entropy_bins)
perfect_grid_entropy = stats.entropy(perfect_grid)


# In[ ]:


# bearing and entropy functions
def reverse_bearing(x):
    return x + 180 if x < 180 else x - 180


def get_unweighted_bearings(G, threshold):
    # calculate edge bearings
    # threshold lets you discard streets < some length from the bearings analysis
    b = pd.Series([d['bearing'] for u, v, k, d in G.edges(keys=True, data=True) if d['length'] > threshold])
    return pd.concat([b, b.map(reverse_bearing)]).reset_index(drop='True')


def count_and_merge(n, bearings):
    # make twice as many bins as desired, then merge them in pairs
    # prevents bin-edge effects around common values like 0° and 90°
    n = n * 2
    bins = np.arange(n + 1) * 360 / n
    count, _ = np.histogram(bearings, bins=bins)
    
    # move the last bin to the front, so eg 0.01° and 359.99° will be binned together
    count = np.roll(count, 1)
    return count[::2] + count[1::2]


def calculate_entropy(data, n):
    bin_counts = count_and_merge(n, data)
    entropy = stats.entropy(bin_counts)
    return entropy


def calculate_orientation_entropy(Gu, threshold=10, entropy_bins=entropy_bins):
    # make network undirected then get edge bearings and calculate entropy
    Gu = ox.add_edge_bearings(Gu)
    bearings = get_unweighted_bearings(Gu, threshold=threshold)
    entropy = calculate_entropy(bearings.dropna(), entropy_bins)
    return entropy


def calculate_orientation_order(orientation_entropy, entropy_bins=entropy_bins, perfect_grid_entropy=perfect_grid_entropy):
    max_entropy = np.log(entropy_bins)    
    orientation_order = 1 - ((orientation_entropy - perfect_grid_entropy) / (max_entropy - perfect_grid_entropy)) ** 2
    return orientation_order


# In[ ]:


def calculate_circuity(G, edge_length_total):
    
    coords = np.array([[G.nodes[u]['y'], G.nodes[u]['x'], G.nodes[v]['y'], G.nodes[v]['x']] for u, v, k in G.edges(keys=True)])
    df_coords = pd.DataFrame(coords, columns=['u_y', 'u_x', 'v_y', 'v_x'])

    gc_distances = ox.great_circle_vec(lat1=df_coords['u_y'],
                                       lng1=df_coords['u_x'],
                                       lat2=df_coords['v_y'],
                                       lng2=df_coords['v_x'])

    gc_distances = gc_distances.fillna(value=0)
    circuity_avg = edge_length_total / gc_distances.sum()
    return circuity_avg


def intersection_counts(G, tolerance=clean_int_tol):
    
    node_ids = set(G.nodes())
    streets_per_node = G.graph['streets_per_node']
    intersection_count = len([True for node, count in streets_per_node.items() if (count > 1) and (node in node_ids)])
    intersection_count_clean = len(ox.clean_intersections(ox.project_graph(G),
                                                          tolerance=tolerance,
                                                          dead_ends=False))
    return intersection_count, intersection_count_clean


# In[ ]:


# calculate elevation & grade stats
def elevation_grades(G):
    
    grades = pd.Series(nx.get_edge_attributes(G, 'grade_abs'))
    elevs = pd.Series(nx.get_node_attributes(G, 'elevation'))
    elev_iqr = elevs.quantile(0.75) - elevs.quantile(0.25)
    elev_range = elevs.max() - elevs.min()
    
    return grades.mean(), grades.median(), elevs.mean(), elevs.median(), elevs.std(), elev_range, elev_iqr


# In[ ]:


def save_results(indicators, output_path):
    df = pd.DataFrame(indicators).T.reset_index(drop=True)
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(ox.ts(), f'saved {len(indicators)} results to disk')
    return df


# In[ ]:


def calculate_graph_indicators(filepath):
    
    Gu = ox.get_undirected(ox.load_graphml(filepath, folder=''))
    
    # street lengths, 
    lengths = pd.Series(nx.get_edge_attributes(Gu, 'length'))
    length_median = lengths.median()
    length_mean = lengths.mean()
    
    # nodes, edges, and node degree
    n = len(Gu.nodes())
    m = len(Gu.edges())
    k_avg = 2 * m / n
    
    # proportion of 4-way intersections, 3-ways, and dead-ends
    prop_4way = list(Gu.graph['streets_per_node'].values()).count(4) / len(Gu.nodes())
    prop_3way = list(Gu.graph['streets_per_node'].values()).count(3) / len(Gu.nodes())
    prop_deadend = list(Gu.graph['streets_per_node'].values()).count(1) / len(Gu.nodes())
    
    # average circuity and straightness
    circuity = calculate_circuity(Gu, lengths.sum())
    straightness = 1 / circuity
    
    # elevation and grade
    grade_mean, grade_median, elev_mean, elev_median, elev_std, elev_range, elev_iqr = elevation_grades(Gu)
    
    # total and clean intersection counts
    intersect_count, intersect_count_clean = intersection_counts(Gu)
    
    # bearing/orientation entropy/order
    orientation_entropy = calculate_orientation_entropy(Gu)
    orientation_order = calculate_orientation_order(orientation_entropy)    
    
    # assemble and return results as dict
    return {'circuity'              : circuity,
            'elev_iqr'              : elev_iqr,
            'elev_mean'             : elev_mean,
            'elev_median'           : elev_median,
            'elev_range'            : elev_range,
            'elev_std'              : elev_std,
            'grade_mean'            : grade_mean,
            'grade_median'          : grade_median,
            'intersect_count'       : intersect_count,
            'intersect_count_clean' : intersect_count_clean,
            'k_avg'                 : k_avg,
            'length_mean'           : length_mean,
            'length_median'         : length_median,
            'm'                     : m,
            'n'                     : n,
            'orientation_entropy'   : orientation_entropy,
            'orientation_order'     : orientation_order,
            'prop_4way'             : prop_4way,
            'prop_3way'             : prop_3way,
            'prop_deadend'          : prop_deadend,
            'straightness'          : straightness}            


# In[ ]:


if os.path.exists(indicators_path):
    indicators = pd.read_csv(indicators_path).set_index('uc_id', drop=False).T.to_dict()
else:
    indicators = {}


# In[ ]:


counter = 0
for country_folder in sorted(os.listdir(graphml_folder)):
    for filename in sorted(os.listdir(os.path.join(graphml_folder, country_folder))):
        
        # get filepath and country/city identifiers
        filepath = os.path.join(graphml_folder, country_folder, filename)
        country, country_iso = country_folder.split('-')
        core_city, uc_id = filename.replace('.graphml', '').split('-')
        uc_id = int(uc_id)
        
        if uc_id in indicators:
            # already have indicator results for this one, so skip it
            print(ox.ts(), 'already got', country, country_iso, core_city, uc_id)
        else:
            # calculate indicators for this graph
            print(ox.ts(), 'processing', filepath)
            result = {'country'    : country,
                      'country_iso': country_iso,
                      'core_city'  : core_city,
                      'uc_id'      : uc_id}
            result.update(calculate_graph_indicators(filepath))
            indicators[uc_id] = result

            # save periodically
            counter += 1
            if counter % save_every_n == 0:
                df = save_results(indicators, indicators_path)


# In[ ]:


# final save to disk
df = save_results(indicators, indicators_path)


# In[ ]:




