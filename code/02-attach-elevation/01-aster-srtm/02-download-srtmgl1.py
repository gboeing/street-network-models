#!/usr/bin/env python

import json
import multiprocessing as mp
from pathlib import Path
from zipfile import ZipFile

import osmnx as ox
import pandas as pd
import requests

# username/password for https://www.earthdata.nasa.gov/
from keys import pwd, usr

# load configs
with open("./config.json") as f:
    config = json.load(f)

# configurations
cpus = 4
urls_path = config["gdem_srtm_urls_path"]
dl_path = Path(config["gdem_srtm_path"])
dl_path.mkdir(parents=True, exist_ok=True)


def download(url, usr=usr, pwd=pwd, dl_path=dl_path):
    with requests.Session() as session:
        filename = Path(url).name
        session.trust_env = False
        request = session.request("get", url, auth=(usr, pwd))
        response = session.get(request.url, auth=(usr, pwd))

        if response.ok:
            filepath = dl_path / filename
            with filepath.open(mode="wb") as f:
                f.write(response.content)

            with ZipFile(filepath, "r") as z:
                z.extractall(dl_path)
            filepath.unlink()

        else:
            print(response.status_code, response.text)


# get all the URLs
urls = pd.read_csv(urls_path, header=None).iloc[:, 0].sort_values()
print(ox.ts(), f"There are {len(urls):,} total SRTM URLs")

# how many files have already been downloaded?
existing = {fp.name.split(".")[0] for fp in dl_path.glob("*.hgt")}
print(ox.ts(), f"There are {len(existing):,} files already downloaded")

# how many files are remaining to download?
tiles = (Path(url).name.split(".")[0] for url in urls)
remaining = [url for url, tile in zip(urls, tiles) if tile not in existing]
print(ox.ts(), f"Downloading {len(remaining):,} URLs with {cpus} CPUs")

# multiprocess the queue
if len(remaining) > 0:
    args = ((url,) for url in remaining)
    with mp.get_context().Pool(cpus) as pool:
        _ = pool.starmap_async(download, args).get()

file_count = len(list(dl_path.glob("*")))
msg = f"Finished: {file_count:,} files in {str(dl_path)!r}"
print(ox.ts(), msg)
