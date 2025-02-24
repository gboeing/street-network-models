import json
import os

import pandas as pd

# load configs
with open("../config.json") as f:
    config = json.load(f)


# get all the model geopackage filepaths
gpkg_folder = config["models_gpkg_path"]
gpkgs = []
for country in os.listdir(gpkg_folder):
    files = os.listdir(f"{gpkg_folder}/{country}")
    files = [f"{gpkg_folder}/{country}/{file}" for file in files]
    gpkgs.extend(files)


# get all the model graphml filepaths
graphml_folder = config["models_graphml_path"]
graphmls = []
for country in os.listdir(graphml_folder):
    files = os.listdir(f"{graphml_folder}/{country}")
    files = [f"{graphml_folder}/{country}/{file}" for file in files]
    graphmls.extend(files)


# get all the model node/edge list filepaths
nelist_folder = config["models_nelist_path"]
nelists = []
for country in os.listdir(nelist_folder):
    for place in os.listdir(f"{nelist_folder}/{country}"):
        files = os.listdir(f"{nelist_folder}/{country}/{place}")
        files = [f"{nelist_folder}/{country}/{place}/{file}" for file in files]
        nelists.extend(files)


# check that we have the same number of country folders for each file type
lens = len(os.listdir(nelist_folder)), len(os.listdir(gpkg_folder)), len(os.listdir(graphml_folder))
country_check = len(os.listdir(nelist_folder)) == len(os.listdir(gpkg_folder)) == len(os.listdir(graphml_folder))
print("same number of country folders for each file type:", lens, country_check)


# check that we have the same number of gpkg, graphml, and node/edge list files
lens = len(gpkgs), len(graphmls), int(len(nelists) / 2)
file_check = len(gpkgs) == len(graphmls) == int(len(nelists) / 2)
print("same number of files of each type:", lens, file_check)


# check that the same set of country/city names exists across gkpg, graphml, and node/edge lists
gpkg_names = [s.replace(gpkg_folder, "").replace(".gpkg", "") for s in gpkgs]
graphml_names = [s.replace(graphml_folder, "").replace(".graphml", "") for s in graphmls]
nelist_names = [
    s.replace(nelist_folder, "").replace("/node_list.csv", "").replace("/edge_list.csv", "") for s in nelists
]
names_check = set(nelist_names) == set(gpkg_names) == set(graphml_names)
print("same set of names across all file types:", names_check)


# check that an indicator row exists for every graphml file
inds = pd.read_csv(config["indicators_path"])
ucids1 = set(inds["uc_id"].values)
ucids2 = set(int(g.split("-")[-1].split(".")[0]) for g in graphmls)
indicator_check = ucids1 == ucids2
print("indicator rows exist for every graphml file:", indicator_check)


# throw exception if any checks failed
if country_check and file_check and names_check and indicator_check:
    print("ALL CHECKS OK")
else:
    print("WARNING: SOME CHECKS FAILED")
