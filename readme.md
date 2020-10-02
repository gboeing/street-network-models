# World Cities Street Network Analysis

This project models and analyzes the street networks of every urban area in the world. It produces open data repositories of the street network models and the indicators.


## Input data

This project uses the GHSL urban clusters dataset to define the world's urban areas' boundary polygons.

Create a `/data` root folder with a `inputs` subfolder and place the following unzipped data inside it: http://cidportal.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_STAT_UCDB2015MT_GLOBE_R2019A/V1-2/GHS_STAT_UCDB2015MT_GLOBE_R2019A.zip

Urban boundaries dataset citation: Florczyk, A.J., Corbane, C., Schiavina, M., Pesaresi, M., Maffenini, L., Melchiorri, M., Politis, P., Sabo, F., Freire, S., Ehrlich, D., Kemper, T., Tommasi, P., Airaghi, D. and L. Zanchetta. 2019. GHS Urban Centre Database 2015, multitemporal and multidimensional attributes, R2019A. European Commission, Joint Research Centre (JRC) [Dataset] PID: http://data.europa.eu/89h/53473144-b88c-44bc-b4a3-4583ed1f547e

## Workflow

The workflow is organized into folders and scripts.

### 1. Construct models


#### 1.1. Prep data

Load the GHS urban centers dataset, retain useful columns, save as a geopackage file at `/data/inputs/ucs.gpkg`

#### 1.2. Download graphs

Uses OSMnx to download OSM data and construct into a MultiDiGraph of street network. Saves to disk as GraphML. Parameterized to get only drivable streets, retain all, simplify, and truncate by edge. Does this for every urban center's polygon boundary if it meets the following conditions:

  - is marked true positive in urban centers data set
  - has >= 1 km2 built-up area
  - includes at least 3 nodes

Save each graph to disk as a GraphML file at `data/models/graphml/country/city.graphml`.

### 2. Attach elevation

This project uses three data sources for elevation:
  1. ASTER DEM
  2. SRTM3 DEM
  3. Google Maps Elevation API

It uses ASTER and SRTM to attach elevation data to each graph node in each model, then calculate edge grades. Both of these are public, free, open data. It uses Google Maps elevation just as a validation dataset. For easiest replicability, all three are queried via web service APIs rather than PostGIS installations. These APIs are available from third parties for free or low cost.

ASTER is 30m x 30m: fine resolution but noisy (error). [SRTM](https://dds.cr.usgs.gov/srtm/version2_1/Documentation/SRTM_Topo.pdf) is 90m x 90m: coarser resolution but much less noisy (less error), and is processed by CGIAR-CSI to fix further errors and fill voids

#### 2.1. Elevation extract nodes

For each country, open each saved graph's GraphML file, extract the nodes' x and y coordinates and append to a DataFrame of all nodes for the country. Save all the node coordinates for each country to disk in the data folder, one csv file per country.

Steps 2.2 - 2.4 are performed in the `aster-srtm` and `google` subfolders to download elevation data for each node from GeoNames ASTER and SRTM APIs and Google Maps Elevation API. You need API keys.

#### 2.2. Cluster nodes

We want to send node coordinates to the elevation API in batches. But the batches need to consist of (approximately) adjacent nodes. The GeoNames API charges per tile retrieved, so this drastically cuts usage costs. The Google API uses a smoothing function to estimate elevation. If the nodes are from different parts of the planet (or at different elevations), this smoothing will result in very coarse-grained approximations of individual nodes' elevations. So, load all the node coordinates for each country and cluster (then recursively subcluster) them via k-means to get them into spatial clusters no bigger than the max batch size (2000 for GeoNames, 400 for Google) via 4 steps:

  1. Get the initial set of all country nodes into more manageably sized clusters. It's CPU/RAM intensive to divide lots of points into lots of clusters, so this pass just divides lots of points into a few clusters.
  2. Recursively subcluster the clusters to make clusters small enough to be able to cluster into lots of sub-sub-clusters of batch size.
  3. Now that the clusters are of a digestible size, subcluster them down to approximately the batch size.
  4. k-means produces uneven cluster sizes so many will be bigger/smaller than the max batch size. If clustering produced clusters bigger than the max batch size, bissect them (by their currently longest axis) until the are below the batch size.

Save all nodes for all countries in a single CSV file with osmid, x, y, and cluster label.

#### 2.3. Prep URLs

Load the CSV of node clusters and construct an API URL for each with a key.

#### 2.4. Download elevations

Get each URL one at a time. Save node ID + elevation to disk for all nodes.

#### 2.5. Process elevations

Loads ASTER, SRTM, and Google elevation data then selects one of ASTER or SRTM to use as the node elevation value, for each node.

Elevation selection rules:
  1. By default use ASTER as elevation value
  2. Fill ASTER nulls with SRTM values
  3. If ASTER and SRTM differ by more than SRTM spec's error (16 meters [see article](https://www.sciencedirect.com/science/article/abs/pii/S0034425706002008)), use whichever is closer to the Google (validation) value, as tie-breaker.

Finally, save to a CSV file of node elevations.

#### 2.6. Add elevation to nodes

For each country, open each saved graph's GraphML file. Load CSV of node elevations. For each node in each graph, add its elevation as new attribute. Calculate edge grades. Resave graph to disk as GraphML, then save as node/edge lists (csv) and GeoPackage file with node/edge layers.

### 3. Calculate indicators

#### 3.1 Calculate indicators

Load each saved graph's GraphML file. Calculate each indicator as described in the indicators metadata file. Save the results to the `indicators-street.csv` file.

#### 3.2. Merge indicators

Merge the `indicators-street.csv` indicators with the urban centers indicators from the geopackage file described in 1.1. Save to disk with indicators named as described in the indicators metadata file.

#### 3.3. Create metadata

Create metadata files for the graph nodes, graph edges, and indicators.

### 4. Upload repository

#### 4.1. File checks

Before staging files for repository deposit, ensure we have what we expect. Verify that we have the same number of countries for each file type, the same number of gpkg, graphml, and node/edge list files, and that the same set of country/city names exists across gkpg, graphml, and node/edge lists.

#### 4.2. Stage files

Compress and zip all model files (geopackages, graphml, node/edge lists) into a staging area for upload to Dataverse.

#### 4.3. Upload dataverse

Upload to Dataverse using their [native](http://guides.dataverse.org/en/latest/api/native-api.html) and [sword](http://guides.dataverse.org/en/latest/api/sword.html) APIs. First [log in](https://dataverse.harvard.edu) and create an API key if you don't have an active one (they expire annually). If this is a revision to the datasets, create a draft dataset revision on the dataverse (edit > edit metadata > change something > save). Otherwise, if this is the first file upload, create a new dataverse and new empty datasets within it, structured like:

  - Global Urban Street Networks
      - Global Urban Street Networks GeoPackages
      - Global Urban Street Networks GraphML Files
      - Global Urban Street Networks Node/Edge Lists
      - Global Urban Street Networks Indicators
      - Global Urban Street Networks Metadata

Then run the script to upload all the model files automatically to their respective datasets in the dataverse (note, if this a dataset revision, edit the script to set `delete_existing_files = True` to first clear out all the carried over files in the draft). Next, manually upload the indicators files and the metadata files to their respective datasets in the dataverse. Finally, visit the dataverse on the web to publish the draft.

Note that the sword API is just needed to delete files, as this hasn't been implemented in the native API yet as of this writing. The native API handles all the file uploading and metadata (which the sword API only offers limited support for).
