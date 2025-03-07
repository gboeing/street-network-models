import json
import time
import zipfile
from hashlib import md5
from pathlib import Path
from urllib.parse import urljoin

import osmnx as ox
import requests
from keys import dataverse_api_key as api_key

# only set true on first run to erase everything from the draft
delete_existing = False

# lets you skip uploading files if this is supposed to be a dry run
debug_mode = False

# load configs
with open("./config.json") as f:
    config = json.load(f)

# configure the dataverse upload
attempts_max = 3  # how many times to re-try same file upload after error before giving up
pause_error = 10  # seconds to pause after an error
pause_normal = 0  # seconds to pause between uploads
upload_timeout = 1200  # how long to set the timeout for upload via http post

# base URL for working with datasets via dataverse native API
base_url = "https://dataverse.harvard.edu/api/v1/datasets/:persistentId/"

# base URL for working with files via dataverse native API
file_url = "https://dataverse.harvard.edu/api/files/{}"

# define what to upload
manifests = [
    {
        "doi": config["doi_gpkg"],
        "folder": config["staging_gpkg_path"],  # folder of zip files to upload
        "file_desc": "Zip contains GeoPackages of all urban street networks in {}.",
        "file_tags": ["GeoPackage", "Street Network", "Models"],
    },
    {
        "doi": config["doi_graphml"],
        "folder": config["staging_graphml_path"],
        "file_desc": "Zip contains GraphML files of all urban street networks in {}.",
        "file_tags": ["GraphML", "Street Network", "Models"],
    },
    {
        "doi": config["doi_nelist"],
        "folder": config["staging_nelist_path"],
        "file_desc": "Zip contains node/edge list CSV files of all urban street networks in {}.",
        "file_tags": ["Node/Edge List", "Street Network", "Models"],
    },
]


# get all the files that currently exist in the draft or published dataset
def get_server_files(doi, version):
    endpoint = f"versions/:{version}/files?key={api_key}&persistentId={doi}"
    response_json = requests.get(urljoin(base_url, endpoint)).json()
    try:
        return {file["dataFile"]["filename"]: file["dataFile"]["id"] for file in response_json["data"]}
    except KeyError:
        return {}


# find pre-existing draft/published files already uploaded to dataset
def get_preexisting_files(manifests):
    draft_files = {}  # what files have already been uploaded to the draft?
    published_files = {}  # what files exist in the published dataset?
    for manifest in manifests:
        doi = manifest["doi"]
        draft_files[doi] = get_server_files(doi, version="draft")
        published_files[doi] = get_server_files(doi, version="latest-published")
        msg = f"Files in {doi}: {len(published_files[doi])} published, {len(draft_files[doi])} draft."
        print(ox.ts(), msg)
    return draft_files, published_files


# delete all the existing (carried-over) files in the draft datasets
def delete_draft_files(already_uploaded):
    file_ids = [f for d in already_uploaded.values() for f in d.values()]
    print(ox.ts(), f"Deleting {len(file_ids)} draft files...")
    headers = {"X-Dataverse-key": api_key}
    for file_id in file_ids:
        url = file_url.format(file_id=file_id)
        response = requests.delete(url, headers=headers)
        if not response.ok:
            print(ox.ts(), f"Failed to delete {url!r}")


# zip a staged zipped file, open it, and return the buffer. this will
# double-zip the zip files because dataverse unzips zip files when they are
# uploaded. the result is that dataverse will host the original zipped file
def get_file_to_upload(fp, target_filename):
    checksum = md5(fp.open("rb").read()).hexdigest()
    upload_fp = Path(config["staging_folder"]) / "upload_temp.zip"
    with zipfile.ZipFile(file=upload_fp, mode="w") as zf:
        zf.write(fp, arcname=target_filename)
    file = {"file": upload_fp.open("rb")}
    return file, checksum


# configure the file description and tags that appear on dataverse
def get_payload_to_upload(fp, manifest):
    country_name = fp.stem[:-4].replace("_", " ").title()
    description = manifest["file_desc"].format(country_name)
    categories = manifest["file_tags"] + [country_name]
    params = {"description": description, "categories": categories}
    return {"jsonData": json.dumps(params)}


# upload a new file to a dataverse dataset
def upload_file(fp, target_filename, manifest, attempt_count=1):
    print(ox.ts(), f"Uploading {str(fp)!r} to {manifest['doi']!r}")
    if debug_mode:
        return

    file, checksum = get_file_to_upload(fp, target_filename)
    payload = get_payload_to_upload(fp, manifest)
    endpoint = f"add?persistentId={manifest['doi']}&key={api_key}"
    url = urljoin(base_url, endpoint)

    try:
        # upload the file to the server
        with requests.Session() as session:
            start_time = time.time()
            response = session.post(url, data=payload, files=file, timeout=upload_timeout)
            elapsed = time.time() - start_time
        if not response.ok:
            raise Exception(response.text)

        # verify the checksum calculated by the server matches our own
        remote_checksum = response.json()["data"]["files"][0]["dataFile"]["md5"]
        if checksum != remote_checksum:
            raise Exception(f"Checksums do not match: {checksum} and {remote_checksum}")

        print(ox.ts(), f"Response {response.status_code} in {elapsed:,.1f} seconds, checksums match")
        time.sleep(pause_normal)

    except Exception as e:
        print(ox.ts(), e)
        if attempt_count < attempts_max:
            # retry upload if we haven't exceeded max attempts
            attempt_count += 1
            print(ox.ts(), f"Re-trying (attempt {attempt_count} of {attempts_max})")
            time.sleep(pause_error)
            upload_file(fp, target_filename, manifest, attempt_count)
        else:
            print(ox.ts(), "No more attempts for this file, we give up")


# get all draft/published files currently existing on server
draft_files, published_files = get_preexisting_files(manifests)
if delete_existing:
    delete_draft_files(draft_files)
    draft_files, published_files = get_preexisting_files(manifests)

# create arguments to upload all remaining files in all staging folders
args_list = []
for manifest in manifests:
    for fp in sorted(Path(manifest["folder"]).glob("*.zip")):
        target_filename = f"{fp.stem}_{fp.parent.stem}{fp.suffix}"
        if target_filename not in draft_files[manifest["doi"]]:
            args_list.append((fp, target_filename, manifest))

# process the queue
print(ox.ts(), f"Uploading {len(args_list)} staged files...")
for args in args_list:
    upload_file(*args)
