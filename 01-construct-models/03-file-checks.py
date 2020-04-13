#!/usr/bin/env python
# coding: utf-8

import json
import os



# load configs
with open('../config.json') as f:
    config = json.load(f)



gpkg_folder = config['models_gpkg_path']
gpkgs = []
for country in os.listdir(gpkg_folder):
    files = os.listdir(f'{gpkg_folder}/{country}')
    files = [f'{gpkg_folder}/{country}/{file}' for file in files]
    gpkgs.extend(files)





graphml_folder = config['models_graphml_path']
graphmls = []
for country in os.listdir(graphml_folder):
    files = os.listdir(f'{graphml_folder}/{country}')
    files = [f'{graphml_folder}/{country}/{file}' for file in files]
    graphmls.extend(files)





nelist_folder = config['models_nelist_path']
nelists = []
for country in os.listdir(nelist_folder):
    for place in os.listdir(f'{nelist_folder}/{country}'):
        files = os.listdir(f'{nelist_folder}/{country}/{place}')
        files = [f'{nelist_folder}/{country}/{place}/{file}' for file in files]
        nelists.extend(files)





# check that we have the same number of country folders for each file type
print(len(os.listdir(nelist_folder)), len(os.listdir(gpkg_folder)), len(os.listdir(graphml_folder)))
country_check = len(os.listdir(nelist_folder)) == len(os.listdir(gpkg_folder)) == len(os.listdir(graphml_folder))
print('same number of country folders for each file type:', country_check)





# check that we have the same number of gpkg, graphml, and node/edge list files
print(len(gpkgs), len(graphmls), len(nelists))
file_check = len(gpkgs) * 2 == len(graphmls) * 2 == len(nelists)
print('same number of files of each type:', file_check)





# check that the same set of country/city names exists across gkpg, graphml, and node/edge lists
gpkg_names = [s.replace(gpkg_folder, '').replace('.gpkg', '') for s in gpkgs]
graphml_names = [s.replace(graphml_folder, '').replace('.graphml', '') for s in graphmls]
nelist_names = [s.replace(nelist_folder, '').replace('/node_list.csv', '').replace('/edge_list.csv', '') for s in nelists]
names_check = set(nelist_names) == set(gpkg_names) == set(graphml_names)
print('same set of names across all file types:', names_check)







