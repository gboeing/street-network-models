#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import geopandas as gpd
import json
import numpy as np
import osmnx as ox
import pandas as pd

print('osmnx version', ox.__version__)


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)


# In[ ]:


aster = pd.read_csv(config['elevation_aster_elevations_path']).set_index('osmid').sort_index()
print(ox.ts(), 'loaded ASTER elevation data for', len(aster), 'nodes')


# In[ ]:


srtm = pd.read_csv(config['elevation_srtm_elevations_path']).set_index('osmid').sort_index()
print(ox.ts(), 'loaded SRTM elevation data for', len(srtm), 'nodes')


# In[ ]:


google = pd.read_csv(config['elevation_google_elevations_path']).set_index('osmid').sort_index()
print(ox.ts(), 'loaded Google elevation data for', len(google), 'nodes')


# In[ ]:


# confirm same set of node ids in each elevation dataset
assert set(google.index) == set(aster.index) == set(srtm.index)


# In[ ]:


# merge aster, srtm, google into one df then free up memory
df = pd.merge(aster, srtm, left_index=True, right_index=True, suffixes=['_aster', '_srtm'])
df = pd.merge(df, google, left_index=True, right_index=True)
aster = srtm = google = None


# In[ ]:


df = df.rename(columns={'elev':'elev_google',
                        'elev_res':'elev_res_google',
                        'lat_aster':'lat',
                        'lng_aster':'lng'})
cols = ['elev_aster', 'elev_srtm', 'elev_google', 'elev_res_google', 'cluster', 'lat', 'lng']
df = df.reindex(columns=cols)


# In[ ]:


# no row is null in both aster and srtm values
print(ox.ts(), pd.isnull(df['elev_aster']).sum(), 'null ASTER values')
print(ox.ts(), pd.isnull(df['elev_srtm']).sum(), 'null SRTM values')
print(ox.ts(), (pd.isnull(df['elev_aster']) & pd.isnull(df['elev_srtm'])).sum(), 'nodes are null in both ASTER and SRTM')


# In[ ]:


# calculate differences in ASTER, SRTM, and Google elevation values
df['elev_diff_aster_google'] = (df['elev_aster'] - df['elev_google']).fillna(np.inf)
df['elev_diff_srtm_google'] = (df['elev_srtm'] - df['elev_google']).fillna(np.inf)

# In[ ]:


# in each row identify if SRTM or ASTER has smaller absolute difference from Google's value
use_srtm = df['elev_diff_srtm_google'].abs() <= df['elev_diff_aster_google'].abs()
pct = 100 * use_srtm.sum() / len(df)
print(ox.ts(), f'{pct:0.1f}% of nodes will use SRTM values, the rest will use ASTER')



# assign elevation as the SRTM or ASTER value closer to Google's, as a tie-breaker
df['elevation'] = np.nan
df.loc[use_srtm, 'elevation'] = df.loc[use_srtm, 'elev_srtm']
df.loc[~use_srtm, 'elevation'] = df.loc[~use_srtm, 'elev_aster']

# ensure all elevations are non-null
assert pd.notnull(df['elevation']).all()
df['elevation'] = df['elevation'].astype(int)


# In[ ]:


# save elevations to disk for subsequently attaching to graph file's nodes
cols = ['elevation', 'elev_aster', 'elev_srtm', 'elev_google']
df[cols].to_csv(config['elevation_final_path'], index=True, encoding='utf-8')
print(ox.ts(), 'saved', len(df), 'elevations to disk at', config['elevation_final_path'])


# In[ ]:




