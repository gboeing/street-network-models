import json
import multiprocessing as mp
from pathlib import Path

import networkx as nx
import osmnx as ox

with open("./config.json") as f:
    config = json.load(f)
ox.settings.cache_folder = config["osmnx_cache_path"]

# configure multiprocessing
if config["cpus"] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config["cpus"]

# get the paths of all the ASTER/SRTM rasters
srtm_files = sorted(Path(config["gdem_srtm_path"]).glob("*.hgt"))
aster_files = sorted(Path(config["gdem_aster_path"]).glob("*.tif"))
attr_rasters = [("elevation_aster", aster_files), ("elevation_srtm", srtm_files)]


def process_graph(filepath, attr_rasters=attr_rasters):
    G = ox.io.load_graphml(filepath)
    for attr, rasters in attr_rasters:
        # if not all graph nodes have this attr, then add elevation from
        # raster files, rename elevation -> this attr name, then save graph
        if set(G.nodes) != set(nx.get_node_attributes(G, attr)):
            try:
                G = ox.elevation.add_node_elevations_raster(G, rasters, cpus=1)
                for _, data in G.nodes(data=True):
                    data[attr] = data.pop("elevation")
                ox.io.save_graphml(G, filepath)
            except ValueError as e:
                print(e, filepath, attr)


# set up the args
filepaths = sorted(Path(config["models_graphml_path"]).glob("*/*"))
args = ((fp,) for fp in filepaths)

# multiprocess the queue
print(ox.ts(), f"Adding elevation to {len(filepaths):,} graphs with {cpus} CPUs")
with mp.get_context().Pool(cpus) as pool:
    _ = pool.starmap_async(process_graph, args).get()
print(ox.ts(), f"Finished adding elevation to {len(filepaths):,} graphs")
