#!/usr/bin/env python

import json
import multiprocessing as mp
from itertools import batched
from pathlib import Path

import osmnx as ox
import pandas as pd
from keys import api_keys

# google usage limit: 512 locations and 16384 characters per request
precision = 5
coords_per_request = 512
requests_per_key = 39000
chars_per_url = 16384
url_template = (
    "https://maps.googleapis.com/maps/api/elevation/json?locations={locations}&key={{key}}"
)

# load configs
with Path("./config.json").open() as f:
    config = json.load(f)

# configure multiprocessing
cpus = mp.cpu_count() if config["cpus"] == 0 else config["cpus"]

# set up the args
filepaths = sorted(Path(config["elevation_nodeclusters_path"]).glob("*.csv"))
args = ((fp,) for fp in filepaths)
print(ox.ts(), f"Loading node clusters from {len(filepaths):,} files with {cpus} CPUs")

# extract all nodes and coordinates from all graphs
with mp.get_context().Pool(cpus) as pool:
    result = pool.starmap_async(pd.read_csv, args)
    df = pd.concat(result.get(), ignore_index=True).set_index("osmid").sort_index()

df = df[~df.index.duplicated()]
print(ox.ts(), f"There are {len(df):,} unique nodes")


def url_add_locations(label, cluster):
    assert len(cluster) <= coords_per_request
    strings = (f"{y:.{precision}f},{x:.{precision}f}" for y, x in zip(cluster["y"], cluster["x"]))
    locations = "|".join(strings)
    return tuple(cluster.index), url_template.format(locations=locations)


with mp.get_context().Pool(cpus) as pool:
    urls = pool.starmap_async(url_add_locations, df.groupby("cluster")).get()

# then add API keys to URLs, `requests_per_key` at a time
urls_with_keys = []
keys_nodes_urls = zip(api_keys, batched(urls, requests_per_key), strict=True)
for api_key, nodes_urls in keys_nodes_urls:
    for nodes, url in nodes_urls:
        url_with_key = url.format(key=api_key)
        assert len(url_with_key) <= chars_per_url
        urls_with_keys.append((nodes, url_with_key))

# ensure no key is used more times than allowed
df_save = pd.DataFrame(urls_with_keys, columns=["nodes", "url"])
for api_key in api_keys:
    count = df_save["url"].str.contains(api_key).sum()
    print(ox.ts(), f"Created {count:,} URLs using key {api_key!r}")
    assert count <= requests_per_key

# save to disk
save_path = Path(config["elevation_google_urls_path"])
save_path.parent.mkdir(parents=True, exist_ok=True)
df_save.to_csv(save_path, index=False, encoding="utf-8")
print(ox.ts(), f"Saved {len(df_save):,} URLs to {str(save_path)!r}")
