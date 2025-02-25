#!/bin/bash
set -euo pipefail
python ./01-construct-models/01-prep-ghsl.py
python ./01-construct-models/02-download-cache.py
python ./01-construct-models/03-create-graphs.py
python ./02-attach-elevation/01-aster-srtm/01-download-aster_v3.py
python ./02-attach-elevation/01-aster-srtm/02-download-srtmgl1.py
python ./02-attach-elevation/01-aster-srtm/03-build-vrts.py
python ./02-attach-elevation/01-aster-srtm/04-add-node-elevations.py
python ./02-attach-elevation/02-google/01-cluster-nodes.py
python ./02-attach-elevation/02-google/02-make-google-urls.py
python ./02-attach-elevation/02-google/03-download-google-elevations.py
python ./02-attach-elevation/02-google/04-choose-best-elevation.py
python ./03-calculate-indicators/01-calculate-node-bc.py
python ./03-calculate-indicators/02-calculate-indicators.py
#python ./03-calculate-indicators/03-merge-indicators.py
#python ./03-calculate-indicators/04-create-metadata.py
#python ./04-upload-repository/01-file-checks.py
#python ./04-upload-repository/02-stage-files.py
#python ./04-upload-repository/03-upload-dataverse.py
