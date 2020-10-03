#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import geopandas as gpd
import json
import osmnx as ox
import pandas as pd

print('osmnx version', ox.__version__)


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)


# In[ ]:


aster = pd.read_csv(config['elevation_aster_elevations_path']).set_index('osmid').sort_index()
print(ox.ts(), 'loaded aster elevation data for', len(aster), 'nodes')


# In[ ]:


srtm = pd.read_csv(config['elevation_srtm_elevations_path']).set_index('osmid').sort_index()
print(ox.ts(), 'loaded srtm elevation data for', len(srtm), 'nodes')


# In[ ]:


google = pd.read_csv(config['elevation_google_elevations_path']).set_index('osmid').sort_index()
print(ox.ts(), 'loaded google elevation data for', len(google), 'nodes')


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
print(ox.ts(), pd.isnull(df['elev_aster']).sum(), 'null aster values')
print(ox.ts(), pd.isnull(df['elev_srtm']).sum(), 'null srtm values')
print(ox.ts(), (pd.isnull(df['elev_aster']) & pd.isnull(df['elev_srtm'])).sum(), 'nodes are null in both aster and srtm')


# In[ ]:


# calculate differences in ASTER, SRTM, and Google elevation values
df['elev_diff_aster_srtm'] = df['elev_aster'] - df['elev_srtm']
df['elev_diff_aster_google'] = df['elev_aster'] - df['elev_google']
df['elev_diff_srtm_google'] = df['elev_srtm'] - df['elev_google']


# In[ ]:


# by default use ASTER values as elevation, but fill nulls with SRTM values
df['elevation'] = df['elev_aster'].fillna(df['elev_srtm']).astype(int)
cols = df.columns.tolist()[-1:] + df.columns.tolist()[:-1]
df = df[cols]


# In[ ]:


# if ASTER and SRTM differ by more than SRTM spec's error (16 meters),
# use whichever is closer to the Google (validation) value, as tie-breaker
srtm_error = 16
mask1 = df['elev_diff_aster_srtm'].abs() > srtm_error
mask2 = df['elev_diff_aster_google'].abs() > df['elev_diff_srtm_google'].abs()
df_bad = df[mask1 & mask2]

# what % of ASTER values will we replace with SRTM values?
pct = 100 * len(df_bad) / len(df)
print(ox.ts(), f'replace {pct:0.2f}% of rows\' bad aster values with srtm values')

# replace these ASTER values with SRTM values and ensure all elevations are non-null
labels = set(df_bad.index.sort_values())
df.loc[labels, 'elevation'] = df['elev_srtm']
assert pd.notnull(df['elevation']).all()

df['elevation'] = df['elevation'].astype(int)


# In[ ]:


# save elevations to disk for subsequent attaching to graph file's nodes
cols = ['elevation', 'elev_aster', 'elev_srtm']
df[cols].to_csv(config['elevation_final_path'], index=True, encoding='utf-8')
print(ox.ts(), 'saved', len(df), 'elevations to disk at', config['elevation_final_path'])


# In[ ]:




