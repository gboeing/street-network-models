import json
import multiprocessing as mp
from pathlib import Path

import osmnx as ox

# load configs
with open("./config.json") as f:
    config = json.load(f)

# configure multiprocessing
if config["cpus"] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config["cpus"]

# set up save/load folder locations
graphml_folder = Path(config["models_graphml_path"])  # where to load GraphML
gpkg_folder = Path(config["models_gpkg_path"])  # where to save GeoPackages
nelist_folder = Path(config["models_nelist_path"])  # where to save node/edge lists


# function to convert node elevation string -> float -> int
def to_int(value):
    int(float(value))


node_dtypes = {"bc": float, "elevation_aster": to_int, "elevation_srtm": to_int}


def save_graph(graphml_path, gpkg_path, nodes_path, edges_path, node_dtypes=node_dtypes):
    print(ox.ts(), f"Saving {str(graphml_path)!r}", flush=True)

    # load GraphML file and save as GeoPackage to disk
    G = ox.io.load_graphml(graphml_path, node_dtypes=node_dtypes)
    ox.io.save_graph_geopackage(G, gpkg_path)

    # get graph node/edge GeoDataFrames for node/edge lists
    nodes, edges = ox.convert.graph_to_gdfs(G, node_geometry=False, fill_edge_geometry=False)

    # nodes: round floats and organize columns
    node_cols = ["osmid", "x", "y", "elevation", "elevation_aster", "elevation_srtm", "bc", "ref", "highway"]
    nodes = nodes.reset_index().reindex(columns=node_cols)

    # edges: round floats and organize columns
    round_cols = ["grade", "grade_abs", "length"]
    edges[round_cols] = edges[round_cols].round(3)
    edge_cols = [
        "u",
        "v",
        "key",
        "oneway",
        "highway",
        "name",
        "length",
        "grade",
        "grade_abs",
        "reversed",
        "lanes",
        "width",
        "est_width",
        "maxspeed",
        "access",
        "service",
        "bridge",
        "tunnel",
        "area",
        "junction",
        "osmid",
        "ref",
    ]
    edges = edges.drop(columns=["geometry"]).reset_index().reindex(columns=edge_cols)

    # save graph node/edge lists as CSV files to disk
    nodes_path.parent.mkdir(parents=True, exist_ok=True)
    nodes.to_csv(nodes_path, index=False, encoding="utf-8")
    edges.to_csv(edges_path, index=False, encoding="utf-8")


def make_args():
    args = []
    filepaths = sorted(graphml_folder.glob("*/*"))
    print(ox.ts(), f"There are {len(filepaths):,} total GraphML files")

    for fp in filepaths:
        gpkg_path = gpkg_folder / fp.parent.stem / fp.name.replace("graphml", "gpkg")
        nelist_output_folder = nelist_folder / fp.parent.stem / fp.stem
        nodes_path = nelist_output_folder / "node_list.csv"
        edges_path = nelist_output_folder / "edge_list.csv"
        if not (gpkg_path.is_file() and nodes_path.is_file() and edges_path.is_file()):
            args.append((fp, gpkg_path, nodes_path, edges_path))

    print(ox.ts(), f"Saving GeoPackage + node/edge lists for {len(args):,} remaining graphs")
    return args


# multiprocess the queue
with mp.get_context().Pool(cpus) as pool:
    pool.starmap_async(save_graph, make_args()).get()
