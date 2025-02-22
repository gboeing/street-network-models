# In[ ]:


import json
import multiprocessing as mp
import os
import random
import time

import networkx as nx
import numpy as np
import osmnx as ox
import pandas as pd
from scipy import stats

print("osmnx version", ox.__version__)
print("networkx version", nx.__version__)


# In[ ]:


# load configs
with open("../config.json") as f:
    config = json.load(f)

ox.config(log_file=True, logs_folder=config["osmnx_log_path"])

if config["cpus_stats"] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config["cpus_stats"]
print(ox.ts(), "using", cpus, "CPUs")

graphml_folder = config["models_graphml_path"]  # where to load graphml files
indicators_street_path = config["indicators_street_path"]  # where to save output street network indicators
save_every_n = 100  # save results every n cities

clean_int_tol = 10  # meters for intersection cleaning tolerance

entropy_bins = 36
min_entropy_bins = 4  # perfect grid
perfect_grid = [1] * min_entropy_bins + [0] * (entropy_bins - min_entropy_bins)
perfect_grid_entropy = stats.entropy(perfect_grid)


# In[ ]:


# bearing and entropy functions
def reverse_bearing(x):
    return x + 180 if x < 180 else x - 180


def get_unweighted_bearings(Gu, threshold):
    # calculate edge bearings
    # threshold lets you discard streets < some length from the bearings analysis
    b = pd.Series([d["bearing"] for u, v, k, d in Gu.edges(keys=True, data=True) if d["length"] > threshold])
    return pd.concat([b, b.map(reverse_bearing)]).reset_index(drop="True")


def count_and_merge(n, bearings):
    # make twice as many bins as desired, then merge them in pairs
    # prevents bin-edge effects around common values like 0° and 90°
    n = n * 2
    bins = np.arange(n + 1) * 360 / n
    count, _ = np.histogram(bearings, bins=bins)

    # move the last bin to the front, so eg 0.01° and 359.99° will be binned together
    count = np.roll(count, 1)
    return count[::2] + count[1::2]


def calculate_entropy(data, n):
    bin_counts = count_and_merge(n, data)
    entropy = stats.entropy(bin_counts)
    return entropy


def calculate_orientation_entropy(Gu, threshold=10, entropy_bins=entropy_bins):
    # get edge bearings and calculate entropy of undirected network
    Gu = ox.add_edge_bearings(Gu)
    bearings = get_unweighted_bearings(Gu, threshold=threshold)
    entropy = calculate_entropy(bearings.dropna(), entropy_bins)
    return entropy


def calculate_orientation_order(
    orientation_entropy, entropy_bins=entropy_bins, perfect_grid_entropy=perfect_grid_entropy
):
    max_entropy = np.log(entropy_bins)
    orientation_order = 1 - ((orientation_entropy - perfect_grid_entropy) / (max_entropy - perfect_grid_entropy)) ** 2
    return orientation_order


# In[ ]:


def calculate_circuity(Gu, length_total):
    coords = np.array(
        [[Gu.nodes[u]["y"], Gu.nodes[u]["x"], Gu.nodes[v]["y"], Gu.nodes[v]["x"]] for u, v, k in Gu.edges(keys=True)]
    )
    df_coords = pd.DataFrame(coords, columns=["u_y", "u_x", "v_y", "v_x"])

    distances = ox.distance.great_circle_vec(
        lat1=df_coords["u_y"], lng1=df_coords["u_x"], lat2=df_coords["v_y"], lng2=df_coords["v_x"]
    )

    circuity_avg = length_total / distances.fillna(value=0).sum()
    return circuity_avg


def intersection_counts(Gup, spn, tolerance=clean_int_tol):
    node_ids = set(Gup.nodes)
    intersect_count = len([1 for node, count in spn.items() if (count > 1) and (node in node_ids)])

    intersect_count_clean = len(
        ox.consolidate_intersections(Gup, tolerance=tolerance, rebuild_graph=False, dead_ends=False)
    )

    intersect_count_clean_topo = len(
        ox.consolidate_intersections(
            Gup, tolerance=tolerance, rebuild_graph=True, reconnect_edges=False, dead_ends=False
        )
    )

    return intersect_count, intersect_count_clean, intersect_count_clean_topo


def get_clustering(G):
    # get directed graph without parallel edges
    D = ox.get_digraph(G, weight="length")

    # average clustering coefficient for the directed graph ignoring parallel edges
    cc_avg_dir = nx.average_clustering(D)

    # average clustering coefficient (weighted) for the directed graph ignoring parallel edges
    cc_wt_avg_dir = nx.average_clustering(D, weight="length")

    # max pagerank (weighted) in directed graph ignoring parallel edges
    pagerank_max = max(nx.pagerank(D, weight="length").values())

    # get undirected graph without parallel edges
    U = nx.Graph(D)

    # average clustering coefficient for the undirected graph ignoring parallel edges
    cc_avg_undir = nx.average_clustering(U)

    # average clustering coefficient (weighted) for the undirected graph ignoring parallel edges
    cc_wt_avg_undir = nx.average_clustering(U, weight="length")

    return cc_avg_dir, cc_avg_undir, cc_wt_avg_dir, cc_wt_avg_undir, pagerank_max


# calculate elevation & grade stats
def elevation_grades(Gu):
    grades = pd.Series(nx.get_edge_attributes(Gu, "grade_abs"))
    elevs = pd.Series(nx.get_node_attributes(Gu, "elevation"))
    elev_iqr = elevs.quantile(0.75) - elevs.quantile(0.25)
    elev_range = elevs.max() - elevs.min()

    return (
        grades.mean(),
        grades.median(),
        elevs.mean(),
        elevs.median(),
        elevs.std(),
        elev_range,
        elev_iqr,
    )


# In[ ]:


def save_results(indicators, output_path):
    output_folder = output_path[: output_path.rfind("/")]
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df = pd.DataFrame(indicators).T.reset_index(drop=True)
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(ox.ts(), f'saved {len(indicators)} results to disk at "{output_path}"')
    return df


# In[ ]:


def calculate_graph_indicators(graphml_folder, country_folder, filename):
    # get filepath and country/city identifiers
    filepath = os.path.join(graphml_folder, country_folder, filename)
    country, country_iso = country_folder.split("-")
    core_city, uc_id = filename.replace(".graphml", "").split("-")
    uc_id = int(uc_id)

    start_time = time.time()
    print(ox.ts(), "processing", filepath)
    G = ox.load_graphml(filepath=filepath)

    # clustering and pagerank: needs directed representation
    cc_avg_dir, cc_avg_undir, cc_wt_avg_dir, cc_wt_avg_undir, pagerank_max = get_clustering(G)

    # get an undirected representation of this network for everything else
    Gu = ox.get_undirected(G)
    G.clear()
    G = None

    # street lengths
    lengths = pd.Series(nx.get_edge_attributes(Gu, "length"))
    length_total = lengths.sum()
    length_median = lengths.median()
    length_mean = lengths.mean()

    # nodes, edges, node degree, self loops
    n = len(Gu.nodes)
    m = len(Gu.edges)
    k_avg = 2 * m / n
    self_loop_proportion = sum(u == v for u, v, k in Gu.edges) / m

    # proportion of 4-way intersections, 3-ways, and dead-ends
    streets_per_node = nx.get_node_attributes(Gu, "street_count")
    prop_4way = list(streets_per_node.values()).count(4) / n
    prop_3way = list(streets_per_node.values()).count(3) / n
    prop_deadend = list(streets_per_node.values()).count(1) / n

    # average circuity and straightness
    circuity = calculate_circuity(Gu, length_total)
    straightness = 1 / circuity

    # elevation and grade
    grade_mean, grade_median, elev_mean, elev_median, elev_std, elev_range, elev_iqr = elevation_grades(Gu)

    # bearing/orientation entropy/order
    orientation_entropy = calculate_orientation_entropy(Gu)
    orientation_order = calculate_orientation_order(orientation_entropy)

    # total and clean intersection counts
    intersect_count, intersect_count_clean, intersect_count_clean_topo = intersection_counts(
        ox.project_graph(Gu), streets_per_node
    )

    # assemble the results
    rslt = {
        "country": country,
        "country_iso": country_iso,
        "core_city": core_city,
        "uc_id": uc_id,
        "cc_avg_dir": cc_avg_dir,
        "cc_avg_undir": cc_avg_undir,
        "cc_wt_avg_dir": cc_wt_avg_dir,
        "cc_wt_avg_undir": cc_wt_avg_undir,
        "circuity": circuity,
        "elev_iqr": elev_iqr,
        "elev_mean": elev_mean,
        "elev_median": elev_median,
        "elev_range": elev_range,
        "elev_std": elev_std,
        "grade_mean": grade_mean,
        "grade_median": grade_median,
        "intersect_count": intersect_count,
        "intersect_count_clean": intersect_count_clean,
        "intersect_count_clean_topo": intersect_count_clean_topo,
        "k_avg": k_avg,
        "length_mean": length_mean,
        "length_median": length_median,
        "length_total": length_total,
        "street_segment_count": m,
        "node_count": n,
        "orientation_entropy": orientation_entropy,
        "orientation_order": orientation_order,
        "pagerank_max": pagerank_max,
        "prop_4way": prop_4way,
        "prop_3way": prop_3way,
        "prop_deadend": prop_deadend,
        "self_loop_proportion": self_loop_proportion,
        "straightness": straightness,
    }

    elapsed = time.time() - start_time
    ox.log(f"finished {filepath} in {elapsed:.0f} seconds")
    return rslt


# In[ ]:
indicators = dict()
if cpus == 1:
    if os.path.exists(indicators_street_path):
        indicators = pd.read_csv(indicators_street_path).set_index("uc_id", drop=False).T.to_dict()

    counter = 0
    for country_folder in sorted(os.listdir(graphml_folder)):
        for filename in sorted(os.listdir(os.path.join(graphml_folder, country_folder))):
            _, uc_id = filename.replace(".graphml", "").split("-")
            uc_id = int(uc_id)
            if uc_id in indicators:
                # already have indicator results for this one, so skip it
                print(ox.ts(), "already got", country_folder, filename)
            else:
                # calculate indicators for this graph
                indicators[uc_id] = calculate_graph_indicators(graphml_folder, country_folder, filename)

                # save periodically
                counter += 1
                if counter % save_every_n == 0:
                    df = save_results(indicators, indicators_street_path)
else:
    params = list()
    for country_folder in sorted(os.listdir(graphml_folder)):
        for filename in sorted(os.listdir(os.path.join(graphml_folder, country_folder))):
            params.append((graphml_folder, country_folder, filename))

    # randomly order params so one thread doesn't have to do all the big graphs
    random.shuffle(params)
    print(ox.ts(), "processing", len(params), "graphs")

    # create a pool of worker processes then map function/parameters to them
    pool = mp.Pool(cpus)
    sma = pool.starmap_async(calculate_graph_indicators, params)

    # get the results, close the pool, wait for worker processes to all exit
    results = sma.get()
    pool.close()
    pool.join()

    for result in results:
        indicators[result["uc_id"]] = result


# In[ ]:


# final save to disk
df = save_results(indicators, indicators_street_path)


# In[ ]:
