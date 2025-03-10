#!/usr/bin/env python

import json
import logging as lg
import multiprocessing as mp
import time
from pathlib import Path

import geopandas as gpd
import osmnx as ox

print(ox.ts(), "OSMnx version", ox.__version__)

# load configs
with Path("./config.json").open() as f:
    config = json.load(f)

# configure OSMnx
ox.settings.log_file = True
ox.settings.log_console = False
ox.settings.logs_folder = config["osmnx_log_path"]
ox.settings.cache_folder = config["osmnx_cache_path"]
ox.settings.use_cache = True

# configure queries
network_type = "drive"
retain_all = True
simplify = True
truncate_by_edge = True

# configure multiprocessing
cpus = mp.cpu_count() if config["cpus"] == 0 else config["cpus"]

# load the prepped urban centers dataset
uc_gpkg_path = config["uc_gpkg_path"]
ucs = gpd.read_file(uc_gpkg_path).sort_values("GH_BUS_TOT_2025", ascending=False)
msg = f"Loaded urban centers data with shape {ucs.shape} from {uc_gpkg_path!r}"
print(ox.ts(), msg)


def get_graph(uc, root) -> None:
    try:
        country_folder = f"{uc['GC_CNT_GAD_2025']}-{uc['country_iso']}"
        uc_filename = f"{uc['GC_UCN_MAI_2025']}-{uc['ID_UC_G0']}.graphml"
        filepath = root / country_folder / uc_filename
        if not filepath.is_file():
            G = ox.graph_from_polygon(
                polygon=uc["geometry"],
                network_type=network_type,
                retain_all=retain_all,
                simplify=simplify,
                truncate_by_edge=truncate_by_edge,
            )

            # don't save graphs if they have fewer than 3 nodes
            min_nodes = 3
            if len(G) >= min_nodes:
                ox.save_graphml(G, filepath=filepath)
                print(ox.ts(), f"Saved {filepath}", flush=True)

    except Exception as e:
        ox.log(f'"{filepath}" failed: {e}', level=lg.ERROR)
        print(e, filepath)


ucs = ucs.sample(len(ucs))  # .tail(10)

# create function arguments for multiprocessing
root = Path(config["models_graphml_path"])
cols = ["GC_CNT_GAD_2025", "country_iso", "GC_UCN_MAI_2025", "ID_UC_G0", "geometry"]
args = ((uc[cols].to_dict(), root) for _, uc in ucs.iterrows())

print(ox.ts(), f"Begin creating {len(ucs):,} graphs using {cpus} CPUs")
start_time = time.time()
with mp.get_context().Pool(cpus) as pool:
    pool.starmap_async(get_graph, args).get()

elapsed = time.time() - start_time
msg = f"Finished creating {len(ucs):,} graphs in {elapsed:,.0f} seconds"
print(ox.ts(), msg)
file_count = len(list(root.glob("*/*")))
msg = f"There are {file_count:,} GraphML files in {str(root)!r}"
print(ox.ts(), msg)
