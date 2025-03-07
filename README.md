# Urban Street Network Models and Indicators

This project uses [OSMnx](https://github.com/gboeing/osmnx) to model and analyze the street networks of every urban area in the world then shares the results (models and measures) in an open data [repository](https://dataverse.harvard.edu/dataverse/global-urban-street-networks) in the Harvard Dataverse.

**Citation info**: Boeing, G. 2021. [Street Network Models and Indicators for Every Urban Area in the World](https://doi.org/10.31235/osf.io/f2dqc). *Geographical Analysis*, published online ahead of print. doi:10.31235/osf.io/f2dqc

The following sections provide notes on reproducibility.

## Computing environment

Given the resource requirements, it's best to run the workflow in a high-performance computing cluster, but it's feasible to run it on a well-equipped personal computer.

System requirements:

  - RAM/CPU: minimum of 32gb for single-threaded execution (note: you'll have to edit `config.json` to set the CPU counts to 1). Recommended 128gb + 24 CPU cores for multithreaded execution as parameterized in the config file.
  - Disk space: 2 terabytes.
  - OS: agnostic, but this workflow was developed and tested on Linux.

Runtime environment: create a new [conda](https://conda.io) environment using the `environment.yml` file to install all the necessary packages to run the workflow. You can install a Jupyter kernel in it, if you wish, like `python -m ipykernel install --user --name snm --display-name "Python (snm)"`.

## Input data

Create a project data root folder with a `inputs` subfolder and place the following unzipped data inside it: *link to inputs.zip*

This project uses the Global Human Settlement Layer urban centers dataset to define the world's urban areas' boundary polygons, specifically, their Urban Centre Database 2025:

> Mari Rivero, Ines; Melchiorri, Michele; Florio, Pietro; Schiavina, Marcello; Goch, Katarzyna; Politis, Panagiotis; Uhl, Johannes; Pesaresi, Martino; Maffenini, Luca; Sulis, Patrizia; Crippa, Monica; Guizzardi, Diego; Pisoni, Enrico; Belis, Claudio; Jacome Felix Oom, Duarte; Branco, Alfredo; Mwaniki, Dennis; Kochulem, Edwin; Githira, Daniel; Carioli, Alessandra; Ehrlich, Daniele; Tommasi, Pierpaolo; Kemper, Thomas; Dijkstra, Lewis (2024): GHS-UCDB R2024A - GHS Urban Centre Database 2025. European Commission, Joint Research Centre (JRC) [Dataset] doi: 10.2905/1a338be6-7eaf-480c-9664-3a8ade88cbcd PID: http://data.europa.eu/89h/1a338be6-7eaf-480c-9664-3a8ade88cbcd

## Workflow

The workflow is organized into folders and scripts, as follows.

### 1. Construct models

#### 1.1. Prep data

Load the GHS urban centers dataset, retain useful columns, save as a GeoPackage file.

#### 1.2. Download cache

Uses OSMnx to download OSM raw data to a cache for subsequent (multi-)processing.

#### 1.3. Create graphs

Use cached OSM raw data to construct a MultiDiGraph of each street network. Can be done in parallel with multiprocessing by changing `cpus` config setting. Saves to disk as GraphML file. Parameterized to get only drivable streets, retain all, simplify, and truncate by edge. Does this for every urban center's polygon boundary if it meets the following conditions:

  - is marked with a "high" quality control score
  - has >= 1 km2 built-up area
  - includes at least 3 nodes

### 2. Attach elevation

This project uses three data sources for elevation:

  1. [ASTERv3](https://www.earthdata.nasa.gov/data/instruments/aster) GDEM at 30 meter resolution
  2. [SRTMGL1](https://www.earthdata.nasa.gov/news/nasa-shuttle-radar-topography-mission-srtm-version-30-global-1-arc-second-data-released-over) GDEM at 30 meter resolution with voids filled (version 3.0 global 1 arc second)
  3. Google Maps Elevation API

We use ASTER and SRTM to attach elevation data to each graph node in each model, then calculate edge grades. Both of these are public, free, open data. It uses Google Maps elevation just as a validation dataset. A previous iteration of this project used to use [CGIAR](https://srtm.csi.cgiar.org)'s post-processed SRTM v4.1, but they only provide 90m resolution SRTM data.

The Google elevation validation technique may not be feasible in the future because they are changing their billing scheme in March 2025. Historically, each billing account gets $200 usage credit free each month. The price per HTTP request was $0.005. Therefore you would get up to 200 / 0.005 = 40,000 free requests each month, within the usage limits of 512 locations per request and 6,000 requests per minute. URLs must be properly encoded to be valid and are limited to 16,384 characters for all web services. With three billing accounts, you could process this entire workflow for free once a month.

#### 2.1. ASTER and SRTM

##### 2.1.1. Download ASTER

Download each ASTER DEM tif file (requires NASA EarthData login credentials).

##### 2.1.2. Download SRTM

Download each SRTM DEM hgt file (requires NASA EarthData login credentials).

##### 2.1.3. Build VRTs

Build two VRT virtual raster files (one for all the ASTER files and one for all the SRTM files) for subsequent querying.

##### 2.1.4. Attach node elevations

Load each GraphML file saved in step 1.3 and add SRTM and ASTER elevation attributes to each node by querying the VRTs then resave the GraphML to disk.

#### 2.2. Google Elevation

##### 2.2.1. Cluster nodes

We want to send node coordinates to the elevation API in batches. But the batches need to consist of (approximately) adjacent nodes because the Google API uses a smoothing function to estimate elevation. If the nodes are from different parts of the planet (or at different elevations), this smoothing will result in very coarse-grained approximations of individual nodes' elevations. So, load all the node coordinates for each graph and spatially cluster them into equal-size clusters of 512 coordinates apiece, then save as a CSV file.

##### 2.2.2. Make URLs

Load the CSV file of node clusters and construct an API URL for each, with a key (requires 3 Google API keys to perform this many API calls for free). Note: the Google billing scheme is changing in March 2025, rendering Google elevation data collection at this scale (likely) infeasible in the future without substantial funding to pay for it.

##### 2.2.3. Download Google elevations

Request each URL and save node ID and elevation to disk for all nodes.

#### 2.2.4. Choose best elevation

Load each GraphML file and select either ASTER or SRTM to use as the official node elevation value, for each node, based on which is closer to the Google value (as a tie-breaker). Then calculate all edge grades and add as edge attributes. Re-save graph to disk as GraphML.

### 3. Calculate stats

#### 3.1. Calculate betweenness centrality

Load each GraphML file and calculate length-weighted node betweenness centrality for all nodes, using IGraph.

#### 3.2. Calculate stats

Load each saved graph's GraphML file. Calculate each stat as described in the metadata file.

#### 3.3. Merge stats

Merge the street network stats with the urban centers stats (from the GeoPackage file created in step 1.1). Save to disk with measures named as described in the metadata file.

#### 3.4. Create metadata

Create metadata files for the graphs (node/edge attributes) and stats.

### 4. Upload repository

#### 4.1. Generate files

Save graphs to disk as GeoPackages and node/edge list files. Then ensure we have what we expect: verify that we have the same number of countries for each file type, the same number of gpkg, graphml, and node/edge list files, and that the same set of country/city names exists across gkpg, graphml, and node/edge lists.

#### 4.2. Stage files

Compress and zip all model files (GeoPackages, GraphML, node/edge lists) into a staging area for upload to Dataverse.

#### 4.3. Upload to Dataverse

Upload to Dataverse using their v1 [native](https://guides.dataverse.org/en/latest/api/native-api.html) API. First [log in](https://dataverse.harvard.edu) and create an API key if you don't have an active one (they expire annually). If this is a revision to existing datasets, create a draft dataset revision on the Dataverse (edit dataset > metadata > change something > save). Otherwise, if this is the first upload ever, create a new Dataverse and new empty datasets within it, structured like:

  - Global Urban Street Networks
      - Global Urban Street Networks GeoPackages
      - Global Urban Street Networks GraphML Files
      - Global Urban Street Networks Node/Edge Lists
      - Global Urban Street Networks Indicators
      - Global Urban Street Networks Metadata

Then run the script to upload all the repository files automatically to their respective datasets in the Dataverse (note: if this a dataset *revision*, edit the script to set `delete_existing_files = True` to first clear out all the carried-over files in the draft). Next, *manually* upload the measures and metadata files to their respective datasets in the Dataverse. Finally, visit the Dataverse on the web to publish the draft.
