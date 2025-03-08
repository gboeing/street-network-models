#!/usr/bin/env python

import json
from pathlib import Path

import osmnx as ox
import pandas as pd

# load configs
with Path("./config.json").open() as f:
    config = json.load(f)

ind_path = config["indicators_path"]  # indicators data (repo subset)
ind_all_path = config["indicators_all_path"]  # all indicators data
ind_meta_path = config["indicators_metadata_path"]  # indicators metadata (repo subset)
ind_all_meta_path = config["indicators_all_metadata_path"]  # indicators metadata (all)
nodes_meta_path = config["models_metadata_nodes_path"]  # graph nodes metadata
edges_meta_path = config["models_metadata_edges_path"]  # graph edges metadata

# create graph nodes metadata
desc = {}
desc["osmid"] = {"description": "Unique OSM node ID", "type": "int"}
desc["x"] = {"description": "Longitude coordinate (EPSG:4326)", "type": "float"}
desc["y"] = {"description": "Latitude coordinate (EPSG:4326)", "type": "float"}
desc["elevation"] = {
    "description": "Node elevation (meters above sea level) from ASTER or SRTM",
    "type": "int",
}
desc["elevation_aster"] = {
    "description": "Node elevation (meters above sea level) from ASTER",
    "type": "int",
}
desc["elevation_srtm"] = {
    "description": "Node elevation (meters above sea level) from SRTM",
    "type": "int",
}
desc["street_count"] = {
    "description": "Number of physical street segments connected to this node",
    "type": "int",
}
desc["bc"] = {
    "description": "Normalized distance-weighted node betweenness centrality",
    "type": "float",
}
desc["other attributes"] = {"description": "As defined in OSM documentation", "type": ""}

# save nodes metadata to disk
nodes_meta = pd.DataFrame(desc).T.reset_index().rename(columns={"index": "indicator"})
nodes_meta.to_csv(nodes_meta_path, index=False, encoding="utf-8")
print(ox.ts(), f"Saved graph nodes metadata to {str(nodes_meta_path)!r}")

# create graph edges metadata
desc = {}
desc["u"] = {"description": "Unique OSM ID of source node", "type": "int"}
desc["v"] = {"description": "Unique OSM ID of destination node", "type": "int"}
desc["key"] = {"description": "Unique ID if parallel edges exist between u and v", "type": "int"}
desc["osmid"] = {"description": "Unique OSM way ID", "type": "int"}
desc["geometry"] = {"description": "Edge centerline geometry (EPSG:4326)", "type": "linestring"}
desc["length"] = {"description": "Length along the edge (meters)", "type": "float"}
desc["grade"] = {"description": "Edge grade (rise over run)", "type": "float"}
desc["grade_abs"] = {"description": "Absolute value of edge grade", "type": "float"}
desc["oneway"] = {"description": "Whether edge part of a one-way street", "type": "boolean"}
desc["reversed"] = {"description": "Whether edge runs opposite direction of OSM way", "type": "boolean"}
desc["other attributes"] = {"description": "As defined in OSM documentation", "type": ""}

# save edges metadata to disk
edges_meta = pd.DataFrame(desc).T.reset_index().rename(columns={"index": "indicator"})
edges_meta.to_csv(edges_meta_path, index=False, encoding="utf-8")
print(ox.ts(), f"Saved graph edges metadata to {str(edges_meta_path)!r}")

# create indicators metadata
desc = {}
desc["area_km2"] = "Area within urban center boundary polygon, km2 (GHS)"
desc["avg_elevation"] = "Average elevation, meters above sea level (GHS)"
desc["avg_precipitation"] = "Annual average precipitation, millimeters (GHS)"
desc["avg_temperature"] = "Average temperature, celsius (GHS)"
desc["bc_gini"] = "Gini coefficient of normalized distance-weighted node betweenness centralities"
desc["bc_max"] = "Max normalized distance-weighted node betweenness centralities"
desc["built_height_m"] = "Average height of built surfaces, meters (GHS)"
desc["built_up_area_m2"] = "Built-up surface area, square meters (GHS)"
desc["built_up_area_percap"] = "Built-up surface area per-capita, square meters per person (GHS)"
desc["cc_avg_dir"] = "Average clustering coefficient (unweighted/directed)"
desc["cc_avg_undir"] = "Average clustering coefficient (unweighted/undirected)"
desc["cc_wt_avg_dir"] = "Average clustering coefficient (weighted/directed)"
desc["cc_wt_avg_undir"] = "Average clustering coefficient (weighted/undirected)"
desc["circuity"] = "Ratio of street lengths to straightline distances"
desc["core_city"] = "Urban center core city name"
desc["country"] = "Primary country name"
desc["country_iso"] = "Primary country ISO 3166-1 alpha-3 code"
desc["elev_iqr"] = "Interquartile range of node elevations, meters"
desc["elev_mean"] = "Mean node elevation, meters"
desc["elev_median"] = "Median node elevation, meters"
desc["elev_range"] = "Range of node elevations, meters"
desc["elev_std"] = "Standard deviation of node elevations, meters"
desc["gdp_ppp"] = "Total GDP PPP, USD (GHS)"
desc["grade_mean"] = "Mean absolute street grade (incline)"
desc["grade_median"] = "Median absolute street grade (incline)"
desc["hdi"] = "Human development index at subnational level (GHS)"
desc["intersect_count"] = "Count of (undirected) edge intersections"
desc["intersect_count_clean"] = "Count of street intersections (merged within 10 meters geometrically)"
desc["intersect_count_clean_topo"] = "Count of street intersections (merged within 10 meters topologically)"
desc["k_avg"] = "Average node degree (undirected)"
desc["koppen_geiger"] = "Köppen-Geiger classification of majority of surface (GHS)"
desc["land_use_efficiency"] = "Land use efficiency 1990-2015 (GHS)"
desc["length_mean"] = "Mean street segment length (undirected edges), meters"
desc["length_median"] = "Median street segment length (undirected edges), meters"
desc["length_total"] = "Total street length (undirected edges), meters"
desc["node_count"] = "Count of nodes"
desc["orientation_entropy"] = "Entropy of street network bearings"
desc["pagerank_max"] = "The maximum PageRank value of any node"
desc["pm25_concentration"] = "Population-weighted average PM2.5 concentrations, micrograms/meter^3 (GHS)"
desc["pop_greenness"] = "Land consumption rate / population growth rate (GHS)"
desc["prop_4way"] = "Proportion of nodes that represent 4-way street intersections"
desc["prop_3way"] = "Proportion of nodes that represent 3-way street intersections"
desc["prop_deadend"] = "Proportion of nodes that represent dead-ends"
desc["resident_pop"] = "Total resident population (GHS)"
desc["self_loop_proportion"] = "Proportion of edges that are self-loops"
desc["straightness"] = "1 / circuity"
desc["street_segment_count"] = "Count of streets (undirected edges)"
desc["transport_co2_em"] = "Total CO2 emissions from transport sector, tons/year (GHS)"
desc["transport_pm25_em"] = "Total PM2.5 emissions from transport sector, tons/year (GHS)"
desc["uc_id"] = "Urban center unique ID (GHS)"
desc["uc_names"] = "List of city names within this urban center (GHS)"
desc["world_bank_income_group"] = "World Bank income group"
desc["world_region"] = "UN SDG geographic region"

# turn the metadata descriptions into a dataframe
meta = pd.DataFrame(desc, index=["description"]).T

# make sure we have metadata for all indicators
ind_all = pd.read_csv(ind_all_path)
assert len(ind_all.columns) == len(meta)

# reindex df so cols are in same order as metadata
ind_all = ind_all.reindex(columns=meta.index).dropna()

# add data type of each field
dtypes = ind_all.dtypes.astype(str).replace({"object": "string"}).str.replace("64", "")
dtypes.name = "type"
meta = meta.merge(right=dtypes, left_index=True, right_index=True).reindex(columns=["type", "description"])

# make sure all the indicators are present in the metadata
assert (meta.index == ind_all.columns).all()

# save all metadata to disk
meta_all = meta.reset_index().rename(columns={"index": "indicator"})
meta_all.to_csv(ind_all_meta_path, index=False, encoding="utf-8")
print(ox.ts(), f"Saved all indicator metadata to {str(ind_all_meta_path)!r}")

# drop fields that should not go in our repo then save
repo_cols = set(pd.read_csv(ind_path).columns)
keep = [k for k in desc if k in repo_cols]
meta = meta.loc[keep].reset_index().rename(columns={"index": "indicator"})
meta.to_csv(ind_meta_path, index=False, encoding="utf-8")
print(ox.ts(), f"Saved repo indicator metadata to {str(ind_meta_path)!r}")
