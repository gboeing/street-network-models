#!/usr/bin/env python

import json
import multiprocessing as mp
import random
from os.path import getsize
from pathlib import Path
from statistics import mean, median

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd

# load configs
with open("./config.json") as f:
    config = json.load(f)

# configure multiprocessing
if config["cpus_stats"] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config["cpus_stats"]

graphml_folder = Path(config["models_graphml_path"])  # where to load graphml files
save_path = Path(config["indicators_street_path"])  # where to save indicator output


def intersection_counts(Gup):
    TOL = 10  # meters for intersection cleaning tolerance
    icc = len(ox.consolidate_intersections(Gup, tolerance=TOL, rebuild_graph=False))
    ict = len(ox.consolidate_intersections(Gup, tolerance=TOL, reconnect_edges=False))
    return {
        "intersect_count": ox.stats.intersection_count(Gup),
        "intersect_count_clean": icc,
        "intersect_count_clean_topo": ict,
    }


def calculate_clustering(G):
    results = {}

    # get directed graph without parallel edges
    G = ox.convert.to_digraph(G, weight="length")

    # avg clust coeff for directed graph ignoring parallel edges
    results["cc_avg_dir"] = nx.average_clustering(G)

    # avg clust coeff (weighted) for directed graph ignoring parallel edges
    results["cc_wt_avg_dir"] = nx.average_clustering(G, weight="length")

    # max pagerank (weighted) in directed graph ignoring parallel edges
    results["pagerank_max"] = max(nx.pagerank(G, weight="length").values())

    # get undirected graph without parallel edges
    G = nx.Graph(G)

    # avg clust coeff for undirected graph ignoring parallel edges
    results["cc_avg_undir"] = nx.average_clustering(G)

    # avg clust coeff (weighted) for undirected graph ignoring parallel edges
    results["cc_wt_avg_undir"] = nx.average_clustering(G, weight="length")
    return results


def calculate_elevation_grades(Gu):
    # calculate elevation & grade stats
    grades = pd.Series(nx.get_edge_attributes(Gu, "grade_abs").values())
    elevs = pd.Series(nx.get_node_attributes(Gu, "elevation").values())
    elev_iqr = elevs.quantile(0.75) - elevs.quantile(0.25)
    elev_range = elevs.max() - elevs.min()
    return {
        "elev_iqr": elev_iqr,
        "elev_mean": elevs.mean(),
        "elev_median": elevs.median(),
        "elev_range": elev_range,
        "elev_std": elevs.std(),
        "grade_mean": grades.mean(),
        "grade_median": grades.median(),
    }


def gini(x):
    sorted_x = np.sort(x)
    n = len(x)
    cumx = np.cumsum(sorted_x, dtype=float)
    return (n + 1 - 2 * np.sum(cumx) / cumx[-1]) / n


def save_results(results, save_path):
    save_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(results)
    if save_path.is_file():
        df = pd.concat([pd.read_csv(save_path), df])
    df.to_csv(save_path, index=False, encoding="utf-8")
    print(ox.ts(), f"Saved {len(results):,} new results to disk at {str(save_path)!r}")


def calculate_graph_stats(graphml_path):
    print(ox.ts(), f"Processing {str(graphml_path)!r}")
    G = ox.io.load_graphml(graphml_path, node_dtypes={"bc": float})

    # get filepath and country/city identifiers
    country, country_iso = graphml_path.parent.stem.split("-")
    core_city, uc_id = graphml_path.stem.split("-")
    uc_id = int(uc_id)

    # clustering and pagerank: needs directed representation
    clustering_stats = calculate_clustering(G)

    # get an undirected representation of this network for everything else
    Gu = ox.convert.to_undirected(G)
    G.clear()
    G = None

    # street lengths
    lengths = nx.get_edge_attributes(Gu, "length").values()
    length_total = sum(lengths)
    length_mean = mean(lengths)
    length_median = median(lengths)

    # nodes, edges, node degree, self loops
    n = len(Gu.nodes)
    m = len(Gu.edges)
    k_avg = 2 * m / n
    self_loop_proportion = ox.stats.self_loop_proportion(Gu)

    # proportion of 4-way intersections, 3-ways, and dead-ends
    spn = ox.stats.streets_per_node_proportions(Gu)
    prop_4way = spn.get(4, 0)
    prop_3way = spn.get(3, 0)
    prop_deadend = spn.get(0, 0)

    # betweenness centrality stats
    bc = list(nx.get_node_attributes(Gu, "bc").values())
    bc_gini = gini(bc)
    bc_max = max(bc)

    # average circuity and straightness
    circuity = ox.stats.circuity_avg(Gu)
    straightness = 1 / circuity

    # elevation and grade
    elevation_grades = calculate_elevation_grades(Gu)

    # orientation entropy
    orientation_entropy = ox.bearing.orientation_entropy(ox.bearing.add_edge_bearings(Gu))

    # total and clean intersection counts
    intersection_stats = intersection_counts(ox.projection.project_graph(Gu))

    # assemble the results
    results = {
        "country": country,
        "country_iso": country_iso,
        "core_city": core_city,
        "uc_id": uc_id,
        "circuity": circuity,
        "k_avg": k_avg,
        "length_mean": length_mean,
        "length_median": length_median,
        "length_total": length_total,
        "street_segment_count": m,
        "node_count": n,
        "orientation_entropy": orientation_entropy,
        "prop_4way": prop_4way,
        "prop_3way": prop_3way,
        "prop_deadend": prop_deadend,
        "self_loop_proportion": self_loop_proportion,
        "straightness": straightness,
        "bc_gini": bc_gini,
        "bc_max": bc_max,
    }
    results.update(clustering_stats)
    results.update(elevation_grades)
    results.update(intersection_stats)
    return results


# get all the filepaths that don't already have results in the save file
done = set(pd.read_csv(save_path)["uc_id"]) if save_path.is_file() else set()
filepaths = sorted(graphml_folder.glob("*/*"), key=getsize)
args = [(fp,) for fp in filepaths if int(fp.stem.split("-")[1]) not in done]

# randomly order params so one thread doesn't have to do all the big graphs
random.shuffle(args)
msg = f"Calculating stats for {len(args):,} graphs using {cpus} CPUs"
print(ox.ts(), msg)

# multiprocess the queue
with mp.get_context().Pool(cpus) as pool:
    results = pool.starmap_async(calculate_graph_stats, args).get()

# final save to disk
save_results(results, save_path)
