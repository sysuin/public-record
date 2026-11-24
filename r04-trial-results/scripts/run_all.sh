#!/bin/sh
# Re-run R04 end to end:  sh scripts/run_all.sh <raw_dir>
# <raw_dir> is a folder for untrusted downloads (API pages are saved there as gzipped JSON; nothing is executed from it).
# Step 1 resumes if <raw_dir>/state.json exists; use an empty folder for a fresh pull (~35 min at NLM's rate guidance).
set -e
RAW="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"; DATA="$HERE/../data"; CH="$HERE/../charts"
[ -n "$RAW" ] || { echo "usage: sh run_all.sh <raw_dir>"; exit 1; }
mkdir -p "$RAW" "$DATA" "$CH"
python3 -I "$HERE/01_fetch.py"         "$RAW"
python3 -I "$HERE/02_parse.py"         "$RAW" "$RAW/studies.parquet"
python3 -I "$HERE/03_analysis.py"      "$RAW/studies.parquet" "$DATA"
python3 -I "$HERE/04_server_counts.py" "$DATA/server_counts.json"
python3 -I "$HERE/05_verify.py"        "$RAW" "$DATA"
python3 -I "$HERE/06_charts.py"        "$DATA" "$CH"
