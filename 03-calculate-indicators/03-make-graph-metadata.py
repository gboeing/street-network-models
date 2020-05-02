#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import osmnx as ox
import pandas as pd
from collections import OrderedDict


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

indicators_path = config['indicators_path'] #indicators data
indicators_metadata_path = config['indicators_metadata_path'] #output indicators metadata
nodes_metadata_path = config['models_metadata_nodes_path'] #output graph nodes metadata
edges_metadata_path = config['models_metadata_edges_path'] #output graph edges metadata


# In[ ]:


# graph nodes metadata
desc = OrderedDict()
desc['osmid']         = {'description' : 'Unique OSM node ID',
                         'type'        : 'int'}
desc['x']             = {'description' : 'Longitude coordinate (epsg 4326)',
                         'type'        : 'float'}
desc['y']             = {'description' : 'Latitude coordinate (epsg 4326)',
                         'type'        : 'float'}
desc['elevation']     = {'description' : 'Node elevation (meters above sea level)',
                         'type'        : 'float'}
desc['elevation_res'] = {'description' : 'Spatial resolution of elevation calculation',
                         'type'        : 'float'}
desc['other attributes'] = {'description' : 'As defined in OSM documentation',
                            'type'        : ''}

# save metadata to disk
nodes_metadata = pd.DataFrame(desc).T.reset_index().rename(columns={'index':'indicator'})
nodes_metadata.to_csv(nodes_metadata_path, index=False, encoding='utf-8')
print(ox.ts(), 'saved graph nodes metadata to disk', nodes_metadata_path)


# In[ ]:


# graph edges metadata
desc = OrderedDict()
desc['u']        = {'description' : 'Unique OSM ID of source node',
                    'type'        : 'int'}
desc['v']        = {'description' : 'Unique OSM ID of destination node',
                    'type'        : 'int'}
desc['key']      = {'description' : 'Unique ID if parallel edges exist between u and v',
                    'type'        : 'int'}
desc['osmid']    = {'description' : 'Unique OSM node ID',
                    'type'        : 'int'}
desc['geometry'] = {'description' : 'Edge centerline geometry (epsg 4326)',
                    'type'        : 'linestring'}
desc['oneway']   = {'description' : 'If edge is part of a one-way street',
                    'type'        : 'boolean'}
desc['length']   = {'description' : 'Length along the edge (meters)',
                    'type'        : 'float'}
desc['grade']    = {'description' : 'Edge grade (rise over run)',
                    'type'        : 'float'}
desc['grade_abs']= {'description' : 'Absolute value of edge grade',
                    'type'        : 'float'}
desc['other attributes'] = {'description' : 'As defined in OSM documentation',
                            'type'        : ''}

# save metadata to disk
edges_metadata = pd.DataFrame(desc).T.reset_index().rename(columns={'index':'indicator'})
edges_metadata.to_csv(edges_metadata_path, index=False, encoding='utf-8')
print(ox.ts(), 'saved graph edges metadata to disk', edges_metadata_path)


# In[ ]:


#indicators metadata
desc = OrderedDict()
desc['country'] = 'Main country name'
desc['country_iso'] = 'Main country ISO 3166-1 alpha-3 code'
desc['core_city'] = 'Urban center core city name'
desc['uc_id'] = 'Urban center unique ID'
desc['circuity'] = 'Ratio of street lengths to straightline distances'
desc['elev_iqr'] = 'Interquartile range of node elevations, meters'
desc['elev_mean'] = 'Mean node elevation, meters'
desc['elev_median'] = 'Median node elevation, meters'
desc['elev_range'] = 'Range of node elevations, meters'
desc['elev_std'] = 'Standard deviation of node elevations, meter'
desc['elev_res_mean'] = 'Average spatial resolution of elevation calculation'
desc['grade_mean'] = 'Mean absolute street grade (incline)'
desc['grade_median'] = 'Median absolute street grade (incline)'
desc['intersect_count'] = 'Count of (undirected) edge intersections'
desc['intersect_count_clean'] = 'Count of street intersections (after merging nodes within 10m of each other)'
desc['k_avg'] = 'Average node degree (undirected)'
desc['length_mean'] = 'Mean street segment length, meters'
desc['length_median'] = 'Median street segment length, meters'
desc['m'] = 'Count of streets (undirected edges)'
desc['n'] = 'Count of nodes'
desc['orientation_entropy'] = 'Entropy of street network bearings'
desc['orientation_order'] = 'Orientation order of street network bearings'
desc['prop_4way'] = 'Proportion of nodes that represent 4-way street intersections'
desc['prop_3way'] = 'Proportion of nodes that represent 3-way street intersections'
desc['prop_deadend'] = 'Proportion of nodes that represent dead-ends'
desc['straightness'] = '1 / circuity'
desc['uc_names'] = 'List of city names within this urban center (GISCO)'
desc['world_region'] = 'Major geographical region (UN WUP)'
desc['world_subregion'] = 'Geographical region (UN WUP)'
desc['resident_pop'] = 'Total resident population in 2015 (GHS)'
desc['area'] = 'Area within urban center boundary polygon, km2 (GHS)'
desc['built_up_area'] = 'Built-up surface area in 2015, km2 (GHS)'
desc['night_light_em'] = 'Average nighttime light emission in 2015, nano-watts per steradian per cm2 (Weiss)',
desc['gdp_ppp'] = 'Sum of GDP PPP values for 2015, in 2011 USD (Kummu)'
desc['un_income_class'] = 'UN income class (UNDESA)'
desc['un_dev_group'] = 'UN development group (UNDESA)'
desc['transport_co2_em_fossil'] = 'Total transport-sector co2 emissions from non-short-cycle-organic fuels in 2015, 10^3 kg/year (Crippa)'
desc['transport_co2_em_bio'] = 'Total transport-sector co2 emissions from short-cycle-organic fuels in 2015, 10^3 kg/year (Crippa)'
desc['transport_pm25_em'] = 'Total transport-sector emissions of particular matter <2.5 microns in 2015, 10^3 kg/year (Crippa)'
desc['pm25_concentration'] = 'Concentration of particular matter <2.5 microns for 2014, micrograms per cubic meter air (GBD)'
desc['climate_classes'] = 'Climate classes (Rubel)'
desc['avg_elevation'] = 'Average elevation, m above sea level (EORC and JAXA)'
desc['avg_precipitation'] = 'Average precipitation for 2014, mm (Harris)'
desc['avg_temperature'] = 'Average temperature for 2014, celsius (Harris)'
desc['land_use_efficiency'] = 'Land use efficiency 1990-2015 (Melchiorri)'
desc['pct_open_space'] = 'Percent open space (JRC)'
desc['centroid_lng'] = 'Longitude of the area centroid, decimal degrees'
desc['centroid_lat'] = 'Latitude of the area centroid, decimal degrees'

# turn the metadata descriptions into a dataframe
metadata = pd.DataFrame(desc, index=['description']).T

# make sure we have metadata for all indicators
ind = pd.read_csv(indicators_path)
assert (len(ind.columns) == len(metadata))

# reindex df so cols are in same order as metadata
ind = ind.reindex(columns=metadata.index).dropna()

# add data type of each field
dtypes = ind.dtypes.astype(str).replace({'object' : 'string'}).str.replace('64', '')
dtypes.name = 'type'
metadata = metadata.merge(right=dtypes, left_index=True, right_index=True).reindex(columns=['type', 'description'])

# make sure all the indicators are present in the metadata
assert (metadata.index == ind.columns).all()

# save metadata to disk
metadata = metadata.reset_index().rename(columns={'index':'indicator'})
metadata.to_csv(indicators_metadata_path, index=False, encoding='utf-8')
print(ox.ts(), 'saved indicator metadata to disk', indicators_metadata_path)


# In[ ]:




