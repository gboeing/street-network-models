#!/usr/bin/env python

import json
import re
import unicodedata
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd

# load configs
with Path("./config.json").open() as f:
    config = json.load(f)

fp = config["uc_input_path"]
msg = f"Loading all layers from {fp!r}"
print(ox.ts(), msg)

# load all GHS urban centers dataset gpkg together into 1 gdf
col_on = "ID_UC_G0"
suffixes = ("", "_DROP")
layers = list(gpd.list_layers(fp)["name"])
ucs = gpd.read_file(fp, layer=layers[0])
for layer in layers[1:]:
    ucs = ucs.merge(
        gpd.read_file(fp, layer=layer),
        left_on=col_on,
        right_on=col_on,
        how="inner",
        suffixes=suffixes,
    )
drop = [c for c in ucs.columns if "_DROP" in c]
ucs = ucs.drop(columns=drop)

# quality control checks
assert ucs.index.is_unique and ucs.columns.is_unique and ucs.crs is not None

# project to OSMnx's default CRS
ucs = ucs.to_crs(ox.settings.default_crs)
ucs["geometry"] = ucs.make_valid()
print(ox.ts(), "Loaded urban centers data with shape", ucs.shape)

# identify which columns to keep when saving to disk
# comments from GHS_UCDB_GLOBE_R2024A_V1_0/GHS_UCDB_GLOBE_R2024A.pdf
cols = [
    "GC_PLS_SCR_2025",  # plausibility score (quality control)
    "ID_UC_G0",  # urban center ID
    "GC_UCN_MAI_2025",  # name of main city inside urban center
    "GC_UCN_LIS_2025",  # list of names of all cities inside urban center
    "GC_CNT_GAD_2025",  # country name based on GADM dataset
    "country_iso",  # country ISO 3166-1 alpha-3 code
    "GC_DEV_USR_2025",  # UN SDG geographic region
    # population, area, density
    "GC_POP_TOT_2025",  # total population (inhabitants) inside urban center
    "GC_UCA_KM2_2025",  # urban center area in km^2
    "GH_BUS_TOT_2025",  # total built-up area m^2
    "GH_BPC_TOT_2025",  # total built-up area per-capita (m^2/person)
    "GH_BUH_AVG_2020",  # average height of built surfaces (m) at 100m res
    # economic development
    "SC_SEC_GDP_2020",  # total GDP PPP (real? USD)
    "GC_DEV_WIG_2025",  # world bank income group
    "SC_SEC_HDI_2020",  # human development index at subnational level
    # pollution emission and concentration
    "EM_CO2_TRA_2022",  # total CO2 emissions in transport sector (ton/year)
    "EM_PM2_TRA_2022",  # total PM2.5 emissions in transport sector (ton/year)
    "EM_PM2_CON_2020",  # pop-weighted average PM2.5 concentrations (μg/m^3)
    # climate/land use
    "CL_KOP_CUR_2025",  # Köppen-Geiger classification of majority of surface
    "GE_ELV_AVG_2025",  # average elevation (m)
    "CL_B12_CUR_2010",  # average annual precipitation in the decade (mm/year)
    "CL_B01_CUR_2010",  # annual mean temperature in the decade (°C)
    "SD_POP_HGR_2025",  # share of pop living in area of high greenness
    "SD_LUE_LPR_2000_2020",  # land use efficiency = land consump rate / pop growth rate
    "geometry",  # urban center geometry
]

# only retain urban centers with at least 1 sq km of built-up area
# drops 943 out of 11422 rows (8.3%)
ucs = ucs[ucs["GH_BUS_TOT_2025"] > 1e6]

# only retain urban centers with a "high" quality control score
# drops 127 out of 10479 rows (1.2%)
ucs = ucs[ucs["GC_PLS_SCR_2025"] == "High"]

# convert columns to int where needed
cols_int = ["GC_POP_TOT_2025", "SC_SEC_GDP_2020"]
ucs[cols_int] = ucs[cols_int].astype(int)

# add country ISO column from lookup table
iso = pd.read_csv(config["iso_codes_path"]).set_index("name")["alpha3"].to_dict()
ucs["country_iso"] = ucs["GC_CNT_GAD_2025"].replace(iso)
assert pd.notna(ucs["country_iso"]).all()


regex = re.compile("[^0-9a-zA-Z]+")


def clean_str(s, regex=regex):
    # clean up name/country for file naming: get ASCII representation and make
    # everything just lowercase letters and underscores. if normalized name is
    # null, empty string, or 1+ whitespaces then rename it to "unnamed"
    try:
        norm = unicodedata.normalize("NFKD", s).encode("ascii", errors="ignore").decode()
        assert norm != "" and set(norm) != {" "}
    except (AssertionError, TypeError):
        norm = "Unnamed"
    return regex.sub("_", norm).lower().strip("_")


cols_lower = ["GC_UCN_MAI_2025", "GC_CNT_GAD_2025"]
ucs[cols_lower] = ucs[cols_lower].map(clean_str)

# save final dataset to disk
ucs = ucs[cols]
ucs.to_file(config["uc_gpkg_path"], driver="GPKG", encoding="utf-8")
msg = f"Saved urban centers gpkg with shape {ucs.shape} at {config['uc_gpkg_path']!r}"
print(ox.ts(), msg)
