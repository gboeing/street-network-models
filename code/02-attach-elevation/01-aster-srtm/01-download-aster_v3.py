#!/usr/bin/env python

import json
import multiprocessing as mp
from pathlib import Path

import osmnx as ox
import pandas as pd
import requests

# username/password for https://www.earthdata.nasa.gov/
from keys import pwd, usr

# load configs
with Path("./config.json").open() as f:
    config = json.load(f)

# configurations
cpus = 4
urls_path = config["gdem_aster_urls_path"]
dl_path = Path(config["gdem_aster_path"])
dl_path.mkdir(parents=True, exist_ok=True)


def download(url, usr=usr, pwd=pwd, dl_path=dl_path) -> None:
    with requests.Session() as session:
        filename = Path(url).name
        session.trust_env = False
        request = session.request("get", url, auth=(usr, pwd))
        response = session.get(request.url, auth=(usr, pwd))

        if response.ok:
            filepath = dl_path / filename
            with filepath.open(mode="wb") as f:
                f.write(response.content)
        else:
            print(response.status_code, response.text)


# get all the URLs pointing at dem tif files
urls = pd.read_csv(urls_path, header=None).iloc[:, 0].sort_values()
urls = urls[urls.str.endswith("_dem.tif")]
print(ox.ts(), f"There are {len(urls):,} total ASTER URLs")

# how many files have already been downloaded?
existing = {path.name for path in dl_path.glob("*.tif")}
print(ox.ts(), f"There are {len(existing):,} files already downloaded")

# how many files are remaining to download?
urls = [url for url in urls if Path(url).name not in existing]
print(ox.ts(), f"Downloading {len(urls):,} URLs with {cpus} CPUs")

# multiprocess the queue
if len(urls) > 0:
    args = ((url,) for url in urls)
    with mp.get_context().Pool(cpus) as pool:
        _ = pool.starmap_async(download, args).get()

file_count = len(list(dl_path.glob("*")))
msg = f"Finished: {file_count:,} files in {str(dl_path)!r}"
print(ox.ts(), msg)
