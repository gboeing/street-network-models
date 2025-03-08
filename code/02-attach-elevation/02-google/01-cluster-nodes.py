#!/usr/bin/env python

import itertools
import json
import math
import multiprocessing as mp
from pathlib import Path

import numpy as np
import osmnx as ox
from scipy.spatial import cKDTree

# google usage limit: 512 locations per request
coords_per_request = 512

# load configs
with Path("./config.json").open() as f:
    config = json.load(f)

# configure multiprocessing
cpus = mp.cpu_count() if config["cpus"] == 0 else config["cpus"]

graphml_folder = Path(config["models_graphml_path"])
save_folder = Path(config["elevation_nodeclusters_path"])


# return graph nodes' x-y coordinates
def get_graph_nodes(fp):
    return ox.convert.graph_to_gdfs(ox.io.load_graphml(fp), edges=False, node_geometry=False)[["x", "y"]]


# get an iterator of points around the perimeter of nodes' coordinates
def get_perimeter_points(nodes):
    tl = np.array((nodes["x"].min(), nodes["y"].max()))
    t = np.array((nodes["x"].mean(), nodes["y"].max()))
    tr = np.array((nodes["x"].max(), nodes["y"].max()))
    r = np.array((nodes["x"].max(), nodes["y"].mean()))
    br = np.array((nodes["x"].max(), nodes["y"].min()))
    b = np.array((nodes["x"].mean(), nodes["y"].min()))
    bl = np.array((nodes["x"].min(), nodes["y"].min()))
    l = np.array((nodes["x"].min(), nodes["y"].mean()))  # noqa: E741
    points = [tl, t, tr, r, br, b, bl, l]
    multiplier = math.ceil(len(nodes) / coords_per_request / len(points))
    return iter(points * multiplier)


# group the nodes into nearest-neighbor clusters
def get_clusters(nodes):
    nodes_remaining = nodes
    perimeter_points = get_perimeter_points(nodes)
    clusters = []
    while len(nodes_remaining) > 0:
        if len(nodes_remaining) <= coords_per_request:
            labels = nodes_remaining.index
        else:
            # find node nearest to next perimeter point, then get a cluster of
            # its nearest `coords_per_request` neighbors around it
            tree = cKDTree(nodes_remaining[["x", "y"]])
            _, start_pos = tree.query(next(perimeter_points), k=1)
            start_point = nodes_remaining.iloc[start_pos][["x", "y"]]
            _, pos = tree.query(start_point, k=coords_per_request)
            labels = nodes_remaining.iloc[pos].index
        clusters.append(labels)
        nodes_remaining = nodes_remaining.drop(labels)

    # ensure each node has a cluster and each cluster is smaller than max size
    assert set(itertools.chain.from_iterable(clusters)) == set(nodes.index)
    for cluster in clusters:
        assert len(cluster) <= coords_per_request

    return clusters


# load graph, cluster nodes, and save to disk
def cluster_nodes(fp):
    nodes = get_graph_nodes(fp)
    clusters = get_clusters(nodes)
    for count, cluster in enumerate(clusters):
        nodes.loc[cluster, "cluster"] = f"{fp.stem}_{count}"

    save_path = save_folder / (fp.stem + ".csv")
    save_path.parent.mkdir(parents=True, exist_ok=True)
    nodes.to_csv(save_path, index=True, encoding="utf-8")
    msg = f"Clustered {fp.stem!r} {len(nodes):,} nodes into {len(clusters):,} clusters"
    print(ox.ts(), msg, flush=True)


filepaths = sorted(graphml_folder.glob("*/*.graphml"))
args = [(fp,) for fp in filepaths if not (save_folder / (fp.stem + ".csv")).is_file()]
print(ox.ts(), f"Clustering nodes from {len(args):,} remaining GraphML files")

with mp.get_context().Pool(cpus) as pool:
    _ = pool.starmap_async(cluster_nodes, args).get()
