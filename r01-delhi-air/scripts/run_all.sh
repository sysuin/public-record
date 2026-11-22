#!/bin/sh
# Re-run R01 end to end. Usage: sh run_all.sh RAW_DIR   (RAW_DIR = folder for untrusted downloads, outside this repo)
set -e
RAW="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"; DATA="$HERE/../data"; CHARTS="$HERE/../charts"
cd "$RAW"/..   # never run from inside the raw folder
python3 -I "$HERE/fetch_cpcb_bulletins.py" "$RAW/bulletins_a" 2015-04-01 2018-12-31
python3 -I "$HERE/fetch_cpcb_bulletins.py" "$RAW/bulletins_b" 2019-01-01 2022-12-31
python3 -I "$HERE/fetch_cpcb_bulletins.py" "$RAW/bulletins_c" 2023-01-01 2026-11-21
python3 -I "$HERE/fetch_aux.py" "$RAW"
mkdir -p "$RAW/parsed"
python3 -I "$HERE/parse_bulletins.py" A "$RAW/parsed/bulletins_A.csv" "$RAW/bulletins_a" "$RAW/bulletins_b" "$RAW/bulletins_c"
python3 -I "$HERE/parse_bulletins.py" B "$RAW/parsed/bulletins_B.csv" "$RAW/bulletins_a" "$RAW/bulletins_b" "$RAW/bulletins_c"
python3 -I "$HERE/prep_aux.py" "$RAW" "$DATA"
python3 -I "$HERE/analysis.py" "$RAW/parsed/bulletins_A.csv" "$DATA"
python3 -I "$HERE/robustness.py" "$RAW/parsed/bulletins_A.csv" "$DATA"
python3 -I "$HERE/verify.py" "$RAW/parsed/bulletins_A.csv" "$RAW/parsed/bulletins_B.csv" "$RAW" "$DATA"
python3 -I "$HERE/charts.py" "$DATA" "$CHARTS"
