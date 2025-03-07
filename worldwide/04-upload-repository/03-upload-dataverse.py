import hashlib
import json
import time
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import osmnx as ox
import requests
from keys import dataverse_api_key as api_key

delete_existing = False  # only make true on the first run to clear out everything from the draft
debug_mode = False

# load configs
with open("../config.json") as f:
    config = json.load(f)

# configure the dataverse upload
attempts_max = 3  # how many times to re-try same file upload after error before giving up
pause_error = 10  # seconds to pause after an error
pause_normal = 0  # seconds to pause between uploads
upload_timeout = 1200  # how long to set the timeout for upload via http post
base_url = "https://dataverse.harvard.edu/api/v1/datasets/:persistentId/"

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


# get all the filenames that currently exist in the DRAFT dataset
def get_draft_files(doi):
    endpoint = f"versions/:draft/files?key={api_key}&persistentId={doi}"
    response_json = requests.get(urljoin(base_url, endpoint)).json()
    try:
        return {file["dataFile"]["filename"]: file["dataFile"]["id"] for file in response_json["data"]}
    except KeyError:
        return {}


# get all the filenames that currently exist in the latest published dataset
def get_published_files(doi):
    endpoint = f"versions/:latest-published/files?key={api_key}&persistentId={doi}"
    response_json = requests.get(urljoin(base_url, endpoint)).json()
    try:
        return {file["dataFile"]["filename"]: file["dataFile"]["id"] for file in response_json["data"]}
    except KeyError:
        return {}

    # find pre-existing draft/published files already uploaded to dataset


def get_preexisting_files(manifests):
    draft_files = {}  # what files have already been uploaded to the draft?
    published_files = {}  # what files exist in the published version of the dataset?
    for manifest in manifests:
        doi = manifest["doi"]
        draft_files[doi] = get_draft_files(doi)
        published_files[doi] = get_published_files(doi)
        msg = f"Files in {doi}: {len(published_files[doi])} published, {len(draft_files[doi])} draft."
        print(ox.ts(), msg)
    return draft_files, published_files


# delete all the existing (carried-over) files in the draft datasets
def delete_draft_files(already_uploaded):
    file_ids = [f for d in already_uploaded.values() for f in d.values()]
    print(ox.ts(), f"Deleting {len(file_ids)} draft files...")

    headers = {"X-Dataverse-key": api_key}
    for file_id in file_ids:
        url = f"https://dataverse.harvard.edu/api/files/{file_id}"
        response = requests.delete(url, headers=headers)
        if not response.ok:
            print(ox.ts(), f"Failed to delete {url!r}")


# zip a staged zipped file, open it, and return the buffer
# this will double-zip the zip files because dataverse unzips zip files when they are uploaded
# the result is that dataverse hosts the original zipped file
def get_file_to_upload(fp, target_filename):
    upload_fp = Path(config["staging_folder"]) / "upload_temp.zip"
    with zipfile.ZipFile(file=upload_fp, mode="w") as zf:
        zf.write(fp, arcname=target_filename)

    # return zipped zip file in a dict + the md5 checksum of original zip file
    file = {"file": open(upload_fp, mode="rb")}
    checksum = hashlib.md5(open(fp, mode="rb").read()).hexdigest()
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
    response = None
    endpoint = f"add?persistentId={manifest['doi']}&key={api_key}"
    url = urljoin(base_url, endpoint)
    file, checksum = get_file_to_upload(fp, target_filename)
    payload = get_payload_to_upload(fp, manifest)

    print(ox.ts(), f"Uploading {str(fp)!r} to {manifest['doi']!r}")
    if debug_mode:
        return

    try:
        # upload the file to the server
        start_time = time.time()
        session = requests.Session()
        response = session.post(url, data=payload, files=file, timeout=upload_timeout)
        session.close()
        et = time.time() - start_time
        if not response.ok:
            raise Exception(response.text)

        # get the checksum calculated by the server
        response_json = response.json()
        checksum_server = response_json["data"]["files"][0]["dataFile"]["md5"]
        if checksum != checksum_server:
            raise Exception(f"Checksums do not match: {checksum} and {checksum_server}")

        print(ox.ts(), f"Response {response.status_code} in {et:,.1f} seconds and checksums match")
        time.sleep(pause_normal)

    except Exception as e:
        # log exception, then retry upload if we haven't exceeded max attempts
        print(ox.ts(), e)
        if attempt_count < attempts_max:
            attempt_count += 1
            print(ox.ts(), f"Re-trying (attempt {attempt_count} of {attempts_max})")
            time.sleep(pause_error)
            response = upload_file(fp, target_filename, manifest, attempt_count)
        else:
            print(ox.ts(), "No more attempts for this file, we give up")


draft_files, published_files = get_preexisting_files(manifests)
if delete_existing:
    delete_draft_files(draft_files)
    draft_files, published_files = get_preexisting_files(manifests)

# upload each zipped file in each staging folder
args = []
for manifest in manifests[0:2]:
    for fp in sorted(Path(manifest["folder"]).glob("*.zip"))[0:2]:
        target_filename = f"{fp.stem}_{fp.parent.stem}{fp.suffix}"
        if target_filename not in draft_files[manifest["doi"]]:
            args.append((fp, target_filename, manifest))

print(ox.ts(), f"Uploading {len(args)} staged files...")
for a in args:
    upload_file(*a)
