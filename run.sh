#!/bin/bash
eval "$(conda shell.bash hook)"
conda activate ox
#cd ./01-construct-models
#python ./01-prep-data.py
#python ./02-download-cache.py
#python ./03-create-graphs.py
#cd ../02-attach-elevation
#python ./01-elevation-extract-nodes.py
#cd ./aster-srtm
#python ./02-cluster-nodes.py
#python ./03-prep-urls.py
#python ./04a-download-elevations-aster.py
#python ./04b-download-elevations-srtm.py
#cd ../google
#python ./02-cluster-nodes.py
#python ./03-prep-urls.py
#python ./04-download-elevations.py
#cd ..
python ./05-process-elevations.py
python ./06-add-elevation-to-graphs.py
cd ../03-calculate-indicators
python 01-calculate-indicators.py
python 02-merge-indicators.py
python 03-create-metadata.py
cd ../04-upload-repository
python 01-file-checks.py
python 02-stage-files.py
