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

Save each graph to disk as a GraphML file at `data/models/graphml/country/city.graphml`

### 2. Attach elevation

#### 2.1. Elevation extract nodes

For each country, open each saved graph's GraphML file, extract the nodes' x and y coordinates and append to a DataFrame of all nodes for the country. Save all the node coordinates for each country to disk at 

#### 2.2. Cluster nodes

#### 2.3. Prep URLs

#### 2.4. Download elevations

#### 2.5. Add elevation to nodes

### 3. Calculate indicators

#### 3.1 Calculate indicators

#### 3.2. Merge indicators

#### 3.3. Create metadata

### 4. Upload repository

### 5. Analysis
