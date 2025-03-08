#!/usr/bin/env python

import json

import geopandas as gpd
import osmnx as ox
import pandas as pd

# load configs
with open("./config.json") as f:
    config = json.load(f)

uc_gpkg_path = config["uc_gpkg_path"]  # prepped urban centers dataset
ind_street_path = config["indicators_street_path"]  # street network indicators to load
ind_path = config["indicators_path"]  # merged indicators to save for repo upload
ind_all_path = config["indicators_all_path"]  # all merged indicators to save for analysis

# load the UCs dataset
ucs = gpd.read_file(uc_gpkg_path).sort_index().drop(columns=["country_iso"])
print(ox.ts(), f"Loaded urban centers dataset with shape={ucs.shape}")

# load the previously calculated street network indicators dataset
ind = pd.read_csv(ind_street_path)
print(ox.ts(), f"Loaded indicators dataset with shape={ind.shape}")

# rename UC fields to something intelligible
mapper = {
    "GC_UCN_LIS_2025": "uc_names",
    "GC_DEV_USR_2025": "world_region",
    "GC_POP_TOT_2025": "resident_pop",
    "GC_UCA_KM2_2025": "area_km2",
    "GH_BUS_TOT_2025": "built_up_area_m2",
    "GH_BPC_TOT_2025": "built_up_area_percap",
    "GH_BUH_AVG_2020": "built_height_m",
    "SC_SEC_GDP_2020": "gdp_ppp",
    "GC_DEV_WIG_2025": "world_bank_income_group",
    "SC_SEC_HDI_2020": "hdi",
    "EM_CO2_TRA_2022": "transport_co2_em",
    "EM_PM2_TRA_2022": "transport_pm25_em",
    "EM_PM2_CON_2020": "pm25_concentration",
    "CL_KOP_CUR_2025": "koppen_geiger",
    "GE_ELV_AVG_2025": "avg_elevation",
    "CL_B12_CUR_2010": "avg_precipitation",
    "CL_B01_CUR_2010": "avg_temperature",
    "SD_POP_HGR_2025": "pop_greenness",
    "SD_LUE_LPR_2000_2020": "land_use_efficiency",
}

# merge UC data with street network indicators, only keep columns from the
# indicators data set or named in the mapper, then save to disk
df = ind.merge(right=ucs, how="inner", left_on="uc_id", right_on="ID_UC_G0")
df = df.rename(columns=mapper)
df = df[[c for c in df.columns if c in ind.columns or c in mapper.values()]]
df.to_csv(ind_all_path, index=False, encoding="utf-8")
msg = f"Saved all indicators to disk at {str(ind_all_path)!r}, shape={df.shape}"
print(ox.ts(), msg)

# drop columns that should not go in our repo then save
drop = [
    "built_up_area_percap",
    "built_height_m",
    "gdp_ppp",
    "world_bank_income_group",
    "hdi",
    "transport_co2_em",
    "transport_pm25_em",
    "pm25_concentration",
    "koppen_geiger",
    "avg_elevation",
    "avg_precipitation",
    "avg_temperature",
    "pop_greenness",
    "land_use_efficiency",
]
df = df.drop(columns=drop)
df.to_csv(ind_path, index=False, encoding="utf-8")
msg = f"Saved repo indicators to disk at {str(ind_path)!r}, shape={df.shape}"
print(ox.ts(), msg)
