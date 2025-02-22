import json
import multiprocessing as mp
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

# load configs
with open("./config.json") as f:
    config = json.load(f)

# configure multiprocessing
if config["cpus"] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config["cpus"]

# dict to convert elev attrs to correct dtype
elev_attrs = ("elevation_aster", "elevation_srtm")
node_dtypes = {attr: float for attr in elev_attrs}

# load google elevation data for lookup
fp = config["elevation_google_elevations_path"]
renamer = {"elevation": "elevation_google", "resolution": "elevation_google_resolution"}
df_elev = pd.read_csv(fp).rename(columns=renamer).set_index("osmid").sort_index()
print(f"Loaded {len(df_elev):,} Google node elevations")


def set_elevations(fp, df_elev=df_elev, node_dtypes=node_dtypes):
    # load the graph and attach google elevation data
    G = ox.io.load_graphml(fp, node_dtypes=node_dtypes)
    nodes, edges = ox.graph_to_gdfs(G)
    nodes = nodes.join(df_elev)

    # calculate differences in ASTER, SRTM, and Google elevation values
    nodes["elev_diff_aster_google"] = (nodes["elevation_aster"] - nodes["elevation_google"]).fillna(np.inf)
    nodes["elev_diff_srtm_google"] = (nodes["elevation_srtm"] - nodes["elevation_google"]).fillna(np.inf)

    # in each row identify if SRTM or ASTER has smaller absolute difference from Google's value
    use_srtm = nodes["elev_diff_srtm_google"].abs() <= nodes["elev_diff_aster_google"].abs()
    pct = 100 * use_srtm.sum() / len(nodes)
    print(f"{pct:0.1f}% of nodes use SRTM, {100 - pct:0.1f}% use ASTER in {fp.stem!r}")

    # assign elevation as the SRTM or ASTER value closer to Google's, as a tie-breaker
    nodes["elevation"] = np.nan
    nodes.loc[use_srtm, "elevation"] = nodes.loc[use_srtm, "elevation_srtm"]
    nodes.loc[~use_srtm, "elevation"] = nodes.loc[~use_srtm, "elevation_aster"]

    # ensure all elevations are non-null
    assert pd.notnull(nodes["elevation"]).all()
    nodes["elevation"] = nodes["elevation"].astype(int)

    # add elevation to graph nodes, calculate edge grades, then save to disk
    nx.set_node_attributes(G, nodes["elevation"], "elevation")
    G = ox.add_edge_grades(G, add_absolute=True)
    ox.io.save_graphml(G, fp)
    return nodes


# multiprocess the queue
args = list((fp,) for fp in Path(config["models_graphml_path"]).glob("*/*.graphml"))  # [-100:]
msg = f"Setting node elevations for {len(args):,} GraphML files using {cpus} CPUs"
print(ox.ts(), msg)
with mp.get_context().Pool(cpus) as pool:
    result = pool.starmap_async(set_elevations, args)
    results = (r for r in result.get() if r is not None)

# save all nodes' elevation details to disk for later analysis
df = pd.concat(results, ignore_index=False).sort_index()
cols = [c for c in df.columns if "elev" in c]
df = df[cols]
df = df.replace([np.inf, -np.inf], np.nan)
print(df.describe().round(2))
df.to_csv(config["elevation_final_path"], index=True, encoding="utf-8")
