#!/usr/bin/env bash
# Dreams v2 sampling + report, after scripts/dreams_v2_train.sh has finished (one GPU job at a time).
#   bash scripts/dreams_v2_sample.sh baseline_s0
set -euo pipefail
cd "$(dirname "$0")/.."
RUN=${1:-baseline_s0}
PY=.venv/Scripts/python.exe
M=runs/$RUN/dreams_v2/models
for m in $(ls $M); do
  [ -f runs/$RUN/dreams_v2/samples/$m/pool.npy ] || $PY -m gen.dreams_v2 sample runs/$RUN $m
done
for m in $(ls $M | grep '^10m_'); do
  [ -f runs/$RUN/dreams_v2/samples/$m/guided.npy ] || $PY -m gen.dreams_v2 guide runs/$RUN $m
done
$PY -m gen.dreams_v2 report runs/$RUN
echo "[dreams_v2_sample] all done"
