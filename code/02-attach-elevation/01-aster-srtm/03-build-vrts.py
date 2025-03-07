import json
from pathlib import Path

import osmnx as ox

with open("./config.json") as f:
    config = json.load(f)
ox.settings.cache_folder = config["osmnx_cache_path"]
aster_path = Path(config["gdem_aster_path"])
srtm_path = Path(config["gdem_srtm_path"])

# get one sample graph, just to build the VRTs for the first time
filepath = sorted(Path(config["models_graphml_path"]).glob("*/*"))[0]
G = ox.io.load_graphml(filepath)

# build VRT files for the SRTM and ASTER raster files
args = [("srtm", srtm_path, "*.hgt"), ("aster", aster_path, "*.tif")]
for data_source, rasters_path, glob_pattern in args:
    rasters = sorted(rasters_path.glob(glob_pattern))
    msg = f"Building VRT for {len(rasters):,} files from {str(rasters_path)!r}"
    print(ox.ts(), msg)
    G = ox.elevation.add_node_elevations_raster(G, rasters)
    for _, data in G.nodes(data=True):
        data[f"elevation_{data_source}"] = data.pop("elevation")

# show descriptive stats for the elevation values in this one city
cols = ["elevation_aster", "elevation_srtm"]
stats = ox.convert.graph_to_gdfs(G, edges=False)[cols].describe()
print(ox.ts(), stats)
