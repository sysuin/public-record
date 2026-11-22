#!/bin/sh
# R02 end to end:  sh run_all.sh <RAW_JSON_DIR> <WORK_DIR>
# RAW_JSON_DIR = folder of extracted Cricsheet zips (one sub-folder per zip, named by zip stem). WORK_DIR = scratch space.
set -e
HERE=$(cd "$(dirname "$0")" && pwd); DATA="$HERE/../data"
python3 -I "$HERE/01_parse.py" "$1" "$2"
python3 -I "$HERE/02_build.py" "$2" "$DATA"
python3 -I "$HERE/03_repeatability.py" "$2" "$DATA"
python3 -I "$HERE/04_predict.py" "$2" "$DATA"
python3 -I "$HERE/05_crossleague.py" "$2" "$DATA"
python3 -I "$HERE/06_extras.py" "$2" "$DATA"
python3 -I "$HERE/07_charts.py" "$DATA" "$HERE/../charts"
python3 -I "$HERE/verify_independent.py" "$1" "$DATA"
