#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import json
import multiprocessing as mp
import os
import osmnx as ox
import zipfile


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

# map input folders to output folders containing zipped country files
manifest = [{'input': config['models_gpkg_path'],    'output': config['staging_gpkg_path']},
            {'input': config['models_graphml_path'], 'output': config['staging_graphml_path']},
            {'input': config['models_nelist_path'],  'output': config['staging_nelist_path']}]


cpus = mp.cpu_count()

# In[ ]:


# zip a whole directory
def zip_dir(input_path, output_folder, output_file):

    output_path = os.path.join(output_folder, output_file)
    if not os.path.exists(output_path):
        print(ox.ts(), input_path, output_path)

        # create a zip file to contain all the files from the input path
        zf = zipfile.ZipFile(file=output_path, mode='w', compression=zipfile.ZIP_DEFLATED)

        for root, folders, files in os.walk(input_path):
            for file in sorted(files):

                input_file = os.path.join(root, file)
                if '/nelist/' in input_file:
                    # preserve the relative folder structure below country level in zip file
                    arcname = os.path.join(os.path.split(root)[-1], file)
                else:
                    # no subfolders for gpkg or graphml, just files in root
                    arcname = file
                zf.write(filename=input_file, arcname=arcname)

        zf.close()


# In[ ]:


print(ox.ts(), f'begin compressing and staging files using {cpus} CPUs')

params = []
for item in manifest:

    output_folder = item['output']
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for country_folder in sorted(os.listdir(item['input'])):
        input_path = os.path.join(item['input'], country_folder)
        output_file = country_folder + '.zip'
        params.append((input_path, output_folder, output_file))

# create a pool of worker processes
pool = mp.Pool(cpus)

# map the function/parameters to the worker processes
sma = pool.starmap_async(zip_dir, params)

# get the results, close the pool, wait for worker processes to all exit
sma.get()
pool.close()
pool.join()

print(ox.ts(), 'finished compressing and staging files')


# In[ ]:




