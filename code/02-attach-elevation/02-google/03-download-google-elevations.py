#!/usr/bin/env python

import json
import multiprocessing as mp
import time
from ast import literal_eval
from pathlib import Path

import osmnx as ox
import pandas as pd
import requests

# load configs
with Path("./config.json").open() as f:
    config = json.load(f)

# configure multiprocessing
cpus = mp.cpu_count() if config["cpus"] == 0 else config["cpus"]

ox.settings.use_cache = True
ox.settings.log_console = False
ox.settings.log_file = True
ox.settings.logs_folder = config["osmnx_log_path"]
ox.settings.cache_folder = config["osmnx_cache_path"]


def get_elevations(nodes, url, pause=0):
    # check if this request is already in the cache
    cached_response_json = ox._http._retrieve_from_cache(url)
    if cached_response_json is not None:
        response_json = cached_response_json
        ox.log(f"Got URL from cache: {url}")

    # otherwise, request the elevations from the API
    else:
        try:
            ox.log(f"Requesting node elevations from API: {url}")
            time.sleep(pause)
            response = requests.get(url)
            assert response.ok
            response_json = response.json()
            ox._http._save_to_cache(url, response_json, response.ok)
        except Exception as e:
            msg = f"Response: {response.status_code}, {response.reason}, {response.text}, {url}"
            print(ox.ts(), msg, e)
            return None

    # extract the results and, if any, return as dataframe
    results = response_json["results"]
    if results is None:
        return None
    df = pd.DataFrame(results, index=literal_eval(nodes))
    if "elevation" not in df.columns:
        cache_filepath = ox._http._resolve_cache_filepath(url)
        print(ox.ts(), f"No elevation results in {str(cache_filepath)!r}")
        return None
    return df[["elevation", "resolution"]].round(2)


# load the URLs and count how many we already have responses cached for
urls = pd.read_csv(config["elevation_google_urls_path"])
count_cached = 0
count_uncached = 0
for url in urls["url"]:
    if ox._http._check_cache(url) is None:
        count_uncached += 1
    else:
        count_cached += 1

msg = f"Getting {count_cached:,} URLs from cache and {count_uncached:,} from API using {cpus} CPUs"
print(ox.ts(), msg)

# uncomment this if you want to actually hit the API (and pay for it)
assert count_uncached == 0

# download elevations from Google API in parallel
with mp.get_context().Pool(cpus) as pool:
    args = ((nodes_url.nodes, nodes_url.url) for nodes_url in urls.itertuples())
    result = pool.starmap_async(get_elevations, args)
    df = pd.concat(result.get(), ignore_index=False).sort_index()

# save to disk
save_path = Path(config["elevation_google_elevations_path"])
save_path.parent.mkdir(parents=True, exist_ok=True)
df.index.name = "osmid"
df.to_csv(save_path, index=True, encoding="utf-8")
print(ox.ts(), f"Saved {len(df):,} node elevations to disk at {save_path}")
