# In[ ]:


import json

import geopandas as gpd
import osmnx as ox
import pandas as pd

# In[ ]:


# load configs
with open("../config.json") as f:
    config = json.load(f)

uc_gpkg_path = config["uc_gpkg_path"]  # prepped urban centers dataset
indicators_street_path = config["indicators_street_path"]  # street network indicators to load
indicators_path = config["indicators_path"]  # merged indicators to save for repo upload
indicators_all_path = config["indicators_all_path"]  # all merged indicators to save for analysis


# In[ ]:


# load the UCs dataset
ucs = gpd.read_file(uc_gpkg_path).sort_index()
print(ox.ts(), "loaded urban centers dataset with shape", ucs.shape)


# In[ ]:


# load the previously calculated street network indicators dataset
ind = pd.read_csv(indicators_street_path)
print(ox.ts(), "loaded indicators dataset with shape", ind.shape)


# In[ ]:


# rename UC fields to something intelligible
mapper = {
    "UC_NM_LST": "uc_names",
    "GRGN_L1": "world_region",
    "GRGN_L2": "world_subregion",
    "P15": "resident_pop",
    "AREA": "area",
    "B15": "built_up_area",
    "NTL_AV": "night_light_em",
    "GDP15_SM": "gdp_ppp",
    "INCM_CMI": "un_income_class",
    "DEV_CMI": "un_dev_group",
    "E_EC2E_T15": "transport_co2_em_fossil",
    "E_EC2O_T15": "transport_co2_em_bio",
    "E_EPM2_T15": "transport_pm25_em",
    "E_CPM2_T14": "pm25_concentration",
    "E_KG_NM_LST": "climate_classes",
    "EL_AV_ALS": "avg_elevation",
    "E_WR_P_14": "avg_precipitation",
    "E_WR_T_14": "avg_temperature",
    "SDG_LUE9015": "land_use_efficiency",
    "SDG_OS15MX": "pct_open_space",
    "GCPNT_LAT": "centroid_lat",
    "GCPNT_LON": "centroid_lng",
}


# In[ ]:


# merge UC data with street network indicators
df = ind.merge(right=ucs, how="inner", left_on="uc_id", right_on="ID_HDC_G0")
df = df.rename(columns=mapper)

# only keep columns from the indicators data set or named in the mapper
cols_keep = [c for c in df.columns if c in ind.columns or c in mapper.values()]
df = df[cols_keep]


print(ox.ts(), "finished indicators, dataset has shape", df.shape)


df.to_csv(indicators_all_path, index=False, encoding="utf-8")
print(ox.ts(), "saved all indicators to disk", indicators_all_path)


# drop columns that should not go in our repo then save
drop = [
    "night_light_em",
    "gdp_ppp",
    "un_income_class",
    "un_dev_group",
    "transport_co2_em_fossil",
    "transport_co2_em_bio",
    "transport_pm25_em",
    "pm25_concentration",
    "climate_classes",
    "avg_elevation",
    "avg_precipitation",
    "avg_temperature",
    "land_use_efficiency",
    "pct_open_space",
    "centroid_lat",
    "centroid_lng",
]
df = df.drop(columns=drop)
print(ox.ts(), "repo indicators dataset has shape", df.shape)
df.to_csv(indicators_path, index=False, encoding="utf-8")
print(ox.ts(), "saved repo indicators to disk", indicators_path)
