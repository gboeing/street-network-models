#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import hashlib
import json
import os
import osmnx as ox
import requests
import time
import xmltodict
import zipfile
from collections import OrderedDict


# In[ ]:


delete_existing_files = True #only make true on the first run to clear out everything from the draft
debug_mode = False


# In[ ]:


# load configs
with open('../config.json') as f:
    config = json.load(f)

# load api key
with open('keys.json') as f:
    keys = json.load(f)

api_key = keys['dataverse_api_key']

# configure the dataverse upload
host = 'https://dataverse.harvard.edu'
attempts_max = 3      #how many times to re-try same file upload after error before giving up
pause_error = 10      #seconds to pause after an error
pause_normal = 0      #seconds to pause between uploads
upload_timeout = 1200 #how long to set the timeout for upload via http post


# In[ ]:


# define what to upload
manifests = [{'doi'      : keys['doi_gpkg'],
              'folder'   : config['staging_gpkg_path'], #folder of zip files to upload
              'file_desc': 'Zip file contains GeoPackages of all the urban street networks in {}.',
              'file_tags': ['GeoPackage', 'Street Network', 'Models']
             },
             {'doi'      : keys['doi_graphml'],
              'folder'   : config['staging_graphml_path'],
              'file_desc': 'Zip file contains GraphML files of all the urban street networks in {}.',
              'file_tags': ['GraphML', 'Street Network', 'Models']
             },
             {'doi'      : keys['doi_nelist'],
              'folder'   : config['staging_nelist_path'],
              'file_desc': 'Zip file contains node/edge list CSV files of all the urban street networks in {}.',
              'file_tags': ['Node/Edge List', 'Street Network', 'Models']
             }]


# ## Helper functions

# In[ ]:


# what to call the deposited file on the server
def get_server_filename(file_path):
    # example: /data/wc/staging/gpkg/iraq-IRQ.zip -> iraq-IRQ_gpkg.zip
    path, filename_ext = os.path.split(file_path)
    filename, ext = os.path.splitext(filename_ext)
    archive_type = os.path.split(path)[-1]
    archive_name = f'{filename}_{archive_type}{ext}'
    return archive_name


# In[ ]:


# zip a staged zipped file, open it, and return the buffer
# this will double-zip the zip files because dataverse unzips zip files when they are uploaded
# the result is that dataverse hosts the original zipped file
def get_file_to_upload(file_path):

    archive_name = get_server_filename(file_path)
    upload_filepath = os.path.join(config['staging_folder'], 'upload_temp.zip')
    zf = zipfile.ZipFile(file=upload_filepath, mode='w')
    zf.write(file_path, arcname=archive_name)
    zf.close()

    # get the checksum of the original zip file
    with open(file_path, mode='rb') as f:
        md5 = hashlib.md5(f.read()).hexdigest()

    # return the zipped zip file in a dict
    file = {'file': open(upload_filepath, mode='rb')}
    return file, md5


# In[ ]:


# configure the file description and tags that appear on dataverse
def get_payload_to_upload(file_desc, file_tags, filename):

    # extract country name and add it to description and tags
    country_name = filename[:-8].replace('_', ' ').title()
    params = {'description': file_desc.format(country_name),
              'categories' : file_tags + [country_name]}
    param_str = json.dumps(params)
    payload = {'jsonData': param_str}
    return payload


# In[ ]:


# upload a new file to a dataverse dataset
def upload_new_file(folder, filename, doi, file_desc, file_tags, attempt_count=1):

    file_path = os.path.join(folder, filename)
    response = None

    # set up the api endpoint, open the file, and make the payload
    endpoint = f'api/v1/datasets/:persistentId/add?persistentId={doi}&key={api_key}'
    url = f'{host}/{endpoint}'
    file, md5 = get_file_to_upload(file_path)
    payload = get_payload_to_upload(file_desc, file_tags, filename)

    try:
        # upload the file to the server
        print(ox.ts(), f'Uploading "{file_path}" to {doi}')

        if debug_mode:
            pass
        else:
            start_time = time.time()
            session = requests.Session()
            response = session.post(url, data=payload, files=file, timeout=upload_timeout)
            session.close()
            et = time.time() - start_time
            sc = response.status_code

            # check if the server response is ok, if not, throw exception
            response_json = response.json()
            if 'status' in response_json and not response_json['status'] == 'OK':
                raise Exception(response_json['message'])

            # get the checksum calculated by the server
            md5_server = response_json['data']['files'][0]['dataFile']['md5']
            if md5 != md5_server:
                raise Exception(f'Checksums do not match: {md5} and {md5_server}')

            print(ox.ts(), f'Response {sc} in {et:,.1f} seconds and checksums match')
            time.sleep(pause_normal)

    except Exception as e:

        # if any exception is thrown, log it, and retry the upload if we haven't exceeded max number of tries
        print(ox.ts(), e)
        time.sleep(pause_error)

        if attempt_count < attempts_max:
            attempt_count += 1
            print(ox.ts(), f'Re-trying (attempt {attempt_count} of {attempts_max})')
            response = upload_new_file(folder, filename, doi, file_desc, file_tags, attempt_count)
        else:
            print(ox.ts(), 'No more attempts for this file, we give up')

    return response


# In[ ]:


# get all the filenames that currently exist in the DRAFT dataset
def get_uploaded_draft_filenames(doi):

    endpoint = f'api/v1/datasets/:persistentId/versions/:draft/files?key={api_key}&persistentId={doi}'
    url = os.path.join(host, endpoint)
    response = requests.get(url)
    response_json = response.json()

    if 'data' in response_json and len(response_json['data']) > 0:
        uploaded_files = response_json['data']
        uploaded_filenames = [file['dataFile']['filename'] for file in uploaded_files]
    else:
        uploaded_filenames = []

    return uploaded_filenames


# In[ ]:


# get all the filenames that currently exist in the latest published dataset
def get_published_files(doi):

    endpoint = f'api/v1/datasets/:persistentId/versions/:latest-published/files?key={api_key}&persistentId={doi}'
    url = os.path.join(host, endpoint)
    response = requests.get(url)
    response_json = response.json()

    if 'data' in response_json and len(response_json['data']) > 0:
        filelist = response_json['data']
        published_files = {file['dataFile']['filename']:file['dataFile']['id'] for file in filelist}
    else:
        published_files = {}

    return published_files


# In[ ]:


def delete_dataset_files(doi):
    """
    Delete all files from draft dataset at the given DOI.
    """

    host = 'dataverse.harvard.edu'
    url_statement = f'https://{host}/dvn/api/data-deposit/v1.1/swordv2/statement/study/{doi}'
    auth = (api_key, None)
    response = requests.get(url_statement, auth=auth)
    assert response.status_code == 200

    response_dict = xmltodict.parse(response.text)
    if 'entry' not in response_dict['feed']:
        print(ox.ts(), f'No files to delete in {doi}')

    else:
        files = response_dict['feed']['entry']
        if isinstance(files, OrderedDict):
            files = [files]
        print(ox.ts(), f'There are {len(files)} files to delete in {doi}')
        st = time.time()

        i = 0
        for file in files:
            file_name = file['id'].split('/')[-1]
            file_id = file['id'].split('/')[-2]
            url_delete = f'https://{host}/dvn/api/data-deposit/v1.1/swordv2/edit-media/file/{file_id}'
            auth = (api_key, None)
            response = requests.delete(url_delete, auth=auth)
            print(ox.ts(), f'Deleted {file_name} {response}')
            assert response.status_code == 204
            i += 1

        et = int(time.time()-st)
        print(ox.ts(), f'Deleted {i} files in {et} seconds')


# In[ ]:


# find pre-existing files already uploaded to dataset
def get_preexisting_files(manifests):

    already_uploaded = {}
    published_files = {}

    for manifest in manifests:
        doi = manifest['doi']
        # what files have already been uploaded to the draft?
        already_uploaded[doi] = get_uploaded_draft_filenames(doi)
        # what files exist in the published version of the dataset?
        published_files[doi] = get_published_files(doi)
        print(ox.ts(), f"Pre-existing files in {doi}: {len(published_files[doi])} published, {len(already_uploaded[doi])} draft.")

    return already_uploaded, published_files


# ## Run the script

# In[ ]:


st = time.time()
print(ox.ts(), 'Started process')
already_uploaded, published_files = get_preexisting_files(manifests)


# In[ ]:


if delete_existing_files:
    # delete all the existing (carried-over) files in the draft datasets
    for manifest in manifests:
        delete_dataset_files(manifest['doi'])
    already_uploaded, published_files = get_preexisting_files(manifests)


# In[ ]:


for manifest in manifests:

    # upload each file in folder
    for filename in sorted(os.listdir(manifest['folder'])):
        file_path = os.path.join(manifest['folder'], filename)
        server_filename = get_server_filename(file_path)
        if not server_filename in already_uploaded[manifest['doi']]:
            response = upload_new_file(manifest['folder'],
                                       filename,
                                       manifest['doi'],
                                       manifest['file_desc'],
                                       manifest['file_tags'])
        else:
            fp = os.path.join(manifest['folder'], filename)
            print(ox.ts(), f'Already uploaded {fp}')

et = time.time()
print(ox.ts(), f'Script finished in {int(et-st)} seconds.')


# In[ ]:




