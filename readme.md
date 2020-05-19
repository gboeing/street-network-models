# World Cities
world cities street network analysis


## Input data

GHS urban clusters dataset

Create a `/data` root folder with a `inputs` subfolder and place the following unzipped data inside it: http://cidportal.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_STAT_UCDB2015MT_GLOBE_R2019A/V1-2/GHS_STAT_UCDB2015MT_GLOBE_R2019A.zip

Dataset citation: Florczyk, A.J., Corbane, C., Schiavina, M., Pesaresi, M., Maffenini, L., Melchiorri, M., Politis, P., Sabo, F., Freire, S., Ehrlich, D., Kemper, T., Tommasi, P., Airaghi, D. and L. Zanchetta. 2019. GHS Urban Centre Database 2015, multitemporal and multidimensional attributes, R2019A. European Commission, Joint Research Centre (JRC) [Dataset] PID: http://data.europa.eu/89h/53473144-b88c-44bc-b4a3-4583ed1f547e

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

#### 2.1. Elevation extract nodes

For each country, open each saved graph's GraphML file, extract the nodes' x and y coordinates and append to a DataFrame of all nodes for the country. Save all the node coordinates for each country to disk at `data/elevation/nodes/country-nodes/country.csv`.

#### 2.2. Cluster nodes

We want to send node coordinates to the elevation API in batches. But the batches need to consist of (approximately) adjacent nodes. The API uses a smoothing function to estimate elevation. If the nodes are from different parts of the planet (or at different elevations), this smoothing will result in very coarse-grained approximations of individual nodes' elevations. So, load all the node coordinates for each country and cluster (then subcluster) them via k-means to get them into spatial clusters no bigger than the max batch size via 4 steps:

  1. Get the initial set of all country nodes into more manageably sized clusters. It's cpu/mem intensive to divide lots of points into lots of clusters, so this pass just divides lots of points into a few clusters.
  2. Recursively subcluster the clusters to make the clusters small enough to be able to cluster into lots of sub-sub-clusters of batch size.
  3. Now that the clusters are of a digestible size, subcluster them down to approximately the batch size.
  4. k-means produces uneven cluster sizes so many will be bigger/smaller than the max batch size. If clustering produced clusters bigger than the max batch size, bissect them (by their currently longest axis) until the are below the batch size.

Save all nodes for all countries in a single CSV file with osmid, x, y, and cluster label.

#### 2.3. Prep URLs

Load the CSV of node clusters and construct an API URL for each with a key.

#### 2.4. Download elevations

Get each URL one at a time. Save node ID + elevation to disk for all nodes in a CSV file.

#### 2.5. Add elevation to nodes

For each country, open each saved graph's GraphML file. Load CSV of node ID elevations. For each node in graph, add its elevation as new attribute. Calcute edge grades. Resave graph to disk as GraphML, then save as node/edge lists and GeoPackage.

### 3. Calculate indicators

#### 3.1 Calculate indicators

Load each saved graph's GraphML file. Calculate each indicator as described in the indicators metadata file. Save the results to the `indicators-street.csv` file.

#### 3.2. Merge indicators

Merge the `indicators-street.csv` indicators with the urban centers indicators from the geopackage file described in 1.1. Save to disk with indicators named as described in the indicators metadata file.

#### 3.3. Create metadata

Create metadata files for the graph nodes, graph edges, and indicators.

#### 3.4. Validation

See validation notebook.

### 4. Upload repository

#### 4.1. File checks

Before staging files for repository deposit, ensure we have what we expect. Verify that we have the same number of countries for each file type, the same number of gpkg, graphml, and node/edge list files, and that the same set of country/city names exists across gkpg, graphml, and node/edge lists.

### 5. Analysis
