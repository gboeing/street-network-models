#!/usr/bin/env python

import json
import multiprocessing as mp
from os.path import getsize
from pathlib import Path

import igraph as ig
import networkx as nx
import osmnx as ox

# we will calculate length-weighted betweenness centralities
WEIGHT_ATTR = "length"

# load configs
with open("./config.json") as f:
    config = json.load(f)

# configure multiprocessing
if config["cpus"] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config["cpus"]

# configure where to find saved graphs and where to save results
graphml_folder = Path(config["models_graphml_path"])
save_folder = Path(config["node_bc_path"])
save_folder.mkdir(parents=True, exist_ok=True)


def convert_igraph(G_nx, weight_attr):
    # relabel graph nodes as integers for igraph to ingest
    G_nx = nx.relabel.convert_node_labels_to_integers(G_nx)

    # create igraph graph and add nodes/edges
    G_ig = ig.Graph(directed=True)
    G_ig.add_vertices(G_nx.nodes)
    G_ig.add_edges(G_nx.edges(keys=False))

    # add edge weights and ensure values >0 for igraph
    weights = nx.get_edge_attributes(G_nx, weight_attr).values()
    weights = (0.001 if w == 0 else w for w in weights)
    G_ig.es[weight_attr] = list(weights)
    return G_ig


def calculate_bc(fp, save_path, weight_attr=WEIGHT_ATTR):
    print(ox.ts(), f"{str(fp)!r}")

    # load graphml, convert to igraph, calculate bc, and normalize values
    G_nx = ox.io.load_graphml(fp)
    bc_raw = convert_igraph(G_nx, weight_attr).betweenness(weights=weight_attr)
    bc_norm = (x / (len(G_nx) - 1) / (len(G_nx) - 2) for x in bc_raw)
    osmid_bc = dict(zip(G_nx.nodes, bc_norm, strict=True))

    # set graph node attributes and re-save graphml file
    nx.set_node_attributes(G_nx, osmid_bc, name="bc")
    ox.io.save_graphml(G_nx, fp)

    # also save results to disk as JSON
    with save_path.open("w") as f:
        json.dump(osmid_bc, f)


# get graph filepaths for which we have not yet calculated BC, sorted by size
filepaths = sorted(graphml_folder.glob("*/*.graphml"), key=getsize)
savepaths = (save_folder / f"{fp.parent.stem}-{fp.stem}.json" for fp in filepaths)
args = [(fp, sp) for fp, sp in zip(filepaths, savepaths) if not sp.is_file()]
print(ox.ts(), f"There are {len(filepaths):,} total GraphML files")
print(ox.ts(), f"Calculating BC for {len(args):,} remaining graphs")

# multiprocess the queue
with mp.get_context().Pool(cpus) as pool:
    pool.starmap_async(calculate_bc, args).get()

count_done = len(list(save_folder.glob("*.json")))
print(ox.ts(), f"Calculated BC for {count_done:,} graphs")
