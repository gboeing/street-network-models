#!/usr/bin/env python
# coding: utf-8

# In[1]:


import geopandas as gpd
import json
import osmnx as ox
import re
import unicodedata


# In[2]:


# load configs
with open('../config.json') as f:
    config = json.load(f)


# In[3]:


# GHS urban centers dataset
ucs = gpd.read_file(config['uc_input_path'])
ucs = ucs.sort_values('P15', ascending=True).reset_index(drop=True) #sort by pop


# In[4]:


# project to OSMnx's default CRS
assert ucs.crs is not None
ucs = ucs.to_crs(ox.settings.default_crs)
ucs['geometry'] = ucs['geometry'].buffer(0)


# In[5]:


print('loaded urban centers dataset with shape', ucs.shape)


# ## Clean and prep

# In[6]:


# make floats
cols_flt = ['AREA', 'B15']
ucs[cols_flt] = ucs[cols_flt].astype(float)

# make ints
cols_int = ['ID_HDC_G0', 'P15', 'GDP15_SM', 'QA2_1V']
ucs[cols_int] = ucs[cols_int].astype(float).astype(int)


# In[7]:


# clean up strings get make everything lowercase ascii letters and numbers (for clean filenaming)
regex = re.compile('[^0-9a-zA-Z]+')
def clean_str(s, regex=regex):
    # get an ASCII representation
    s = unicodedata.normalize('NFKD', str(s)).encode('ascii', errors='ignore').decode()
    # make everything just lowercase letters and underscores
    s = regex.sub('_', s).lower().strip('_')
    return s

cols = ['UC_NM_MN', 'CTR_MN_NM']
ucs[cols] = ucs[cols].applymap(clean_str).applymap(lambda x: x.lower())


# In[8]:


# if urban center has name "n_a" or "" then rename it "unnamed"
mask = (ucs['UC_NM_MN'] == 'n_a') | (ucs['UC_NM_MN'] == '')
ucs.loc[mask, 'UC_NM_MN'] = 'unnamed'


# ## Save to disk

# In[9]:


# identify which columns to keep when saving to disk
cols = ['QA2_1V',      # quality control code (1=true positive, 0=false positive, >1=uncertain)
        'ID_HDC_G0',   # urban center id
        'UC_NM_MN',    # urban center name
        'CTR_MN_NM',   # country name
        'CTR_MN_ISO',  # country iso
        'UC_NM_LST',   # urban center list of names
        'GRGN_L1',     # world region
        'GRGN_L2',     # world subregion
        
        # population, area, density
        'P15',         # resident population (2015)
        'AREA',        # area in km2
        'B15',         # total built-up area 2015 (km2)
        'BUCAP15',     # surface of built-up area per-person 2015 (sq m per person)
        
        # economic development
        'GDP15_SM',    # gdp ppp 2015 (2011 USD)
        'INCM_CMI',    # UN income class
        'DEV_CMI',     # UN development group
        
        # pollution emission and concentration
        'E_EC2E_T15',  # transport-sector co2 emissions from fossil fuels (2012) 10^3 kg/year
        'E_EC2O_T15',  # transport-sector co2 emissions from bio fuels (2012) 10^3 kg/year
        'E_EPM2_T15',  # transport-sector pm2.5 emissions (2012) 10^3 kg/year
        'E_CPM2_T14',  # pm2.5 concentration (2014) micrograms per cubic meter air
        
        # geography
        'E_KG_NM_LST', # climate classes
        'EL_AV_ALS',   # avg elevation
        'E_WR_P_14',   # avg precipitation
        'E_WR_T_14',   # avg temperature
        'SDG_LUE9015', # land use efficiency
        'SDG_OS15MX',  # percentage open space
        'geometry']

ucs_save = ucs[cols]


# In[10]:


print('saving urban centers dataset with shape', ucs_save.shape, config['uc_gpkg_path'])
ucs_save.to_file(config['uc_gpkg_path'], driver='GPKG', encoding='utf-8')


# In[ ]:




