#!/usr/bin/env python

import json
import logging as lg
import multiprocessing as mp
import time

import geopandas as gpd
import osmnx as ox

print(ox.ts(), "OSMnx version", ox.__version__)

# hardcode CPU count to parallelize it without hammering Overpass server
cpus = 3

# load configs
with open("./config.json") as f:
    config = json.load(f)

# configure OSMnx
ox.settings.log_file = True
ox.settings.log_console = False
ox.settings.logs_folder = config["osmnx_log_path"]
ox.settings.cache_folder = config["osmnx_cache_path"]
ox.settings.use_cache = True
ox.settings.cache_only_mode = True

# configure queries
network_type = "drive"
retain_all = True
simplify = True
truncate_by_edge = True

# load the prepped urban centers dataset
uc_gpkg_path = config["uc_gpkg_path"]
ucs = gpd.read_file(uc_gpkg_path).sort_values("GH_BUS_TOT_2025", ascending=True)
msg = f"Loaded urban centers data with shape {ucs.shape} from {uc_gpkg_path!r}"
print(ox.ts(), msg)


def download_data(name, geometry):
    try:
        ox.graph_from_polygon(
            polygon=geometry,
            network_type=network_type,
            retain_all=retain_all,
            simplify=simplify,
            truncate_by_edge=truncate_by_edge,
        )
    except ox._errors.CacheOnlyInterruptError:
        # error on success, because cache_only_mode is True
        print(ox.ts(), "Finished", name, flush=True)

    except Exception as e:
        ox.log(f'"{name}" failed: {e}', level=lg.ERROR)
        print(name, e)


# ucs = ucs.tail(100).sample(len(ucs))
names = ucs["country_iso"] + "-" + ucs["GC_UCN_MAI_2025"] + "-" + ucs["ID_UC_G0"].astype(str)
args = zip(names, ucs["geometry"])

print(ox.ts(), f"Downloading {len(ucs):,} graphs' data using {cpus} CPUs")
start_time = time.time()

with mp.get_context().Pool(cpus) as pool:
    pool.starmap_async(download_data, args).get()

elapsed = time.time() - start_time
msg = f"Finished caching data for {len(ucs):,} graphs in {elapsed:,.0f} seconds"
print(ox.ts(), msg)
