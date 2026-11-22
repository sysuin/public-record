#!/bin/sh
# Re-run R03 end to end:  sh scripts/run_all.sh <raw_dir>
# <raw_dir> is any empty folder for untrusted downloads (PDFs are fetched into it; nothing is executed from it).
# AAI annexes are fetched by 01c_fetch_aai.py from the AAI Traffic News page.
set -e
RAW="$1"; HERE="$(cd "$(dirname "$0")" && pwd)"; DATA="$HERE/../data"; CH="$HERE/../charts"
mkdir -p "$RAW/pdf" "$RAW/sched" "$RAW/cache" "$DATA/raw"
python3 -I "$HERE/01_fetch.py"            "$HERE/manifest.json" "$RAW/pdf"
python3 -I "$HERE/01b_fetch_schedules.py" "$RAW/sched"
python3 -I "$HERE/01c_fetch_aai.py"       "$RAW/aai"
python3 -I "$HERE/02_parse_reports.py"    "$RAW/pdf" "$RAW/cache" "$DATA/raw"
python3 -I "$HERE/03_parse_schedules.py"  "$RAW/sched" "$DATA/schedule_rows_ws2026.csv"
python3 -I "$HERE/03b_parse_aai.py"       "$RAW/aai" "$DATA/aai_domestic_movements_2026.csv"
python3 -I "$HERE/04_tidy.py"             "$DATA"
python3 -I "$HERE/05_analysis.py"         "$DATA"
python3 -I "$HERE/06_charts.py"           "$DATA" "$CH"
python3 -I "$HERE/07_verify.py"           "$RAW/pdf" "$RAW/sched" "$DATA"
