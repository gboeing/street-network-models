#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import geopandas as gpd
import osmnx as ox
import pandas as pd
from collections import OrderedDict


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)
    
uc_gpkg_path = config['uc_gpkg_path'] #prepped urban centers dataset
indicators_street_path = config['indicators_street_path'] #street network indicators to load
indicators_path = config['indicators_path'] #merged indicators to save
indicators_metadata_path = config['indicators_metadata_path'] #indicators metadata


# In[ ]:


# load the UCs dataset
ucs = gpd.read_file(uc_gpkg_path).sort_values('B15', ascending=False)
print(ox.ts(), 'loaded urban centers dataset with shape', ucs.shape)


# In[ ]:


# load the previously calculated street network indicators dataset
ind = pd.read_csv(indicators_street_path)
print(ox.ts(), 'loaded indicators dataset with shape', ind.shape)


# In[ ]:


# rename UC fields to something intelligible
mapper = {'UC_NM_LST'  : 'uc_names',
          'GRGN_L1'    : 'world_region',
          'GRGN_L2'    : 'world_subregion',
          'P15'        : 'resident_pop',
          'AREA'       : 'area',
          'B15'        : 'built_up_area',
          'BUCAP15'    : 'built_up_area_percap',
          'NTL_AV'     : 'night_light_em',
          'GDP15_SM'   : 'gdp_ppp',
          'INCM_CMI'   : 'un_income_class',
          'DEV_CMI'    : 'un_dev_group',
          'E_EC2E_T15' : 'transport_co2_em_fossil',
          'E_EC2O_T15' : 'transport_co2_em_bio',
          'E_EPM2_T15' : 'transport_pm25_em',
          'E_CPM2_T14' : 'pm25_concentration',
          'E_KG_NM_LST': 'climate_classes',
          'EL_AV_ALS'  : 'avg_elevation',
          'E_WR_P_14'  : 'avg_precipitation',
          'E_WR_T_14'  : 'avg_temperature',
          'SDG_LUE9015': 'land_use_efficiency',
          'SDG_OS15MX' : 'pct_open_space',
          'GCPNT_LAT'  : 'centroid_lat',
          'GCPNT_LON'  : 'centroid_lng'}


# In[ ]:


# merge UC data with street network indicators
df = ind.merge(right=ucs, how='inner', left_on='uc_id', right_on='ID_HDC_G0')
df = df.rename(columns=mapper)

# only keep columns from the indicators data set or named in the mapper
cols_keep = [c for c in df.columns if c in ind.columns or c in mapper.values()]
df = df[cols_keep]
print(ox.ts(), 'merged indicators dataset with shape', df.shape)


# In[ ]:


# calculate final indicators that rely on both street network + UC data

# node density
df['node_density'] = df['n'] / df['area']
df['node_density_built_up'] = df['n'] / df['built_up_area']

# intersection density
df['intersect_density'] = df['intersect_count'] / df['area']
df['intersect_density_built_up'] = df['intersect_count'] / df['built_up_area']

# clean intersection density
df['intersect_density_clean'] = df['intersect_count_clean'] / df['area']
df['intersect_density_clean_built_up'] = df['intersect_count_clean'] / df['built_up_area']

# make emissions indicators per capita
df['transport_co2_em_fossil_percap'] = df['transport_co2_em_fossil'] / df['resident_pop']
df['transport_co2_em_bio_percap'] = df['transport_co2_em_bio']/ df['resident_pop']
df['transport_pm25_em_percap'] = df['transport_pm25_em'] / df['resident_pop']


# In[ ]:


print(ox.ts(), 'finished indicators, dataset has shape', df.shape)


# In[ ]:


df.to_csv(indicators_path, index=False, encoding='utf-8')
print(ox.ts(), 'saved indicators to disk', indicators_path)


# ## All done, write out metadata

# In[ ]:


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
desc['grade_mean'] = 'Mean absolute street grade (incline)'
desc['grade_median'] = 'Median absolute street grade (incline)'
desc['intersect_count'] = 'Count of (undirected) edge intersections'
desc['intersect_count_clean'] = 'Count of street intersections (after merging nodes within 10m of each other)'
desc['intersect_density'] = 'Density of (undirected) edge intersections, per km2 of area'
desc['intersect_density_built_up'] = 'Density of (undirected) edge intersections, per km2 of built-up surface area'
desc['intersect_density_clean'] = 'Density of "clean" street intersections, per km2 of area'
desc['intersect_density_clean_built_up'] = 'Density of "clean" street intersections, per km2 of built-up surface area'
desc['k_avg'] = 'Average node degree (undirected)'
desc['length_mean'] = 'Mean street segment length, meters'
desc['length_median'] = 'Median street segment length, meters'
desc['m'] = 'Count of streets (undirected edges)'
desc['n'] = 'Count of nodes'
desc['node_density'] = 'Density of nodes, per km2 of built-up surface area'
desc['node_density_built_up'] = 'Density of nodes, per km2 of area'
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
desc['built_up_area_percap'] = 'Surface of built-up area per resident in 2015, m2 (GHS)'
desc['night_light_em'] = 'Average nighttime light emission in 2015, nano-watts per steradian per cm2 (Weiss)',
desc['gdp_ppp'] = 'Sum of GDP PPP values for 2015, in 2011 USD (Kummu)'
desc['un_income_class'] = 'UN income class (UNDESA)'
desc['un_dev_group'] = 'UN development group (UNDESA)'
desc['transport_co2_em_fossil'] = 'total transport-sector co2 emissions from non-short-cycle-organic fuels in 2015, 10^3 kg/year (Crippa)'
desc['transport_co2_em_fossil_percap'] = 'transport_co2_em_fossil per resident'
desc['transport_co2_em_bio'] = 'total transport-sector co2 emissions from short-cycle-organic fuels in 2015, 10^3 kg/year (Crippa)'
desc['transport_co2_em_bio_percap'] = 'transport_co2_em_bio per resident'
desc['transport_pm25_em'] = 'total transport-sector emissions of particular matter <2.5 microns in 2015, 10^3 kg/year (Crippa)'
desc['transport_pm25_em_percap'] = 'transport_pm25_em per resident'
desc['pm25_concentration'] = 'concentration of particular matter <2.5 microns for 2014, micrograms per cubic meter air (GBD)'
desc['climate_classes'] = 'Climate classes (Rubel)'
desc['avg_elevation'] = 'Average elevation, m above sea level (EORC and JAXA)'
desc['avg_precipitation'] = 'Average precipitation for 2014, mm (Harris)'
desc['avg_temperature'] = 'Average temperature for 2014, celsius (Harris)'
desc['land_use_efficiency'] = 'Land use efficiency 1990-2015 (Melchiorri)'
desc['pct_open_space'] = 'Percent open space (JRC)'
desc['centroid_lng'] = 'longitude of the area centroid, decimal degrees'
desc['centroid_lat'] = 'latitude of the area centroid, decimal degrees'

# turn the metadata descriptions into a dataframe
metadata = pd.DataFrame(desc, index=['description']).T

# reindex df so cols are in same order as metadata
assert (len(df.columns) == len(metadata))
df = df.reindex(columns=metadata.index)

# add data type of each field
dtypes = df.dtypes.astype(str).replace({'object' : 'string'}).str.replace('64', '')
dtypes.name = 'type'
metadata = metadata.merge(right=dtypes, left_index=True, right_index=True).reindex(columns=['type', 'description'])

# make sure all the indicators are present in the metadata
assert (metadata.index == df.columns).all()


# In[ ]:


# save metadata to disk
metadata.to_csv(indicators_metadata_path, index=True, encoding='utf-8')
print(ox.ts(), 'saved indicator metadata to disk', indicators_metadata_path)


# In[ ]:




