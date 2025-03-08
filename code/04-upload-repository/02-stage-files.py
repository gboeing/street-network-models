#!/usr/bin/env python

import json
import multiprocessing as mp
import zipfile
from pathlib import Path

import osmnx as ox

# load configs
with open("./config.json") as f:
    config = json.load(f)

compression_args = {"compression": zipfile.ZIP_BZIP2, "compresslevel": 9}

# map input folders to output folders containing zipped country files
manifest = [
    {"input": Path(config["models_gpkg_path"]), "output": Path(config["staging_gpkg_path"])},
    {"input": Path(config["models_graphml_path"]), "output": Path(config["staging_graphml_path"])},
    {"input": Path(config["models_nelist_path"]), "output": Path(config["staging_nelist_path"])},
]

# configure CPUs
if config["cpus"] == 0:
    cpus = mp.cpu_count()
else:
    cpus = config["cpus"]


# zip a folder and its contents
def zip_folder(input_folder, output_fp, compression_args=compression_args):
    print(ox.ts(), f"Staging {str(output_fp)!r}", flush=True)
    pattern = "*/*" if "nelist" in str(input_folder) else "*"
    with zipfile.ZipFile(output_fp, mode="w", **compression_args) as zf:
        for input_fp in input_folder.glob(pattern):
            zf.write(input_fp, arcname=Path(input_fp.parent.stem) / input_fp.name)


# assemble input folders to zip + their destination zip file paths
args = []
for item in manifest:
    output_folder = item["output"]
    output_folder.mkdir(parents=True, exist_ok=True)
    for input_folder in item["input"].glob("*"):
        output_fp = output_folder / (input_folder.stem + ".zip")
        if not output_fp.is_file():
            args.append((input_folder, output_fp))

# multiprocess the queue
print(ox.ts(), f"Compressing and staging {len(args)} input files using {cpus} CPUs")
with mp.get_context().Pool(cpus) as pool:
    pool.starmap_async(zip_folder, args).get()

print(ox.ts(), f"Finished compressing and staging {len(args)} input files")
