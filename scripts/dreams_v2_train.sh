#!/usr/bin/env bash
# Dreams v2 training queue, one model at a time (never share the GPU while training).
#   bash scripts/dreams_v2_train.sh baseline_s0
# 10 m Step A models first, then v1 (40 m) retrains of the same two sets for the v1-vs-v2 sheet.
set -euo pipefail
cd "$(dirname "$0")/.."
RUN=${1:-baseline_s0}
PY=.venv/Scripts/python.exe
M=runs/$RUN/dreams_v2/models
mkdir -p "$M"
for s in path_weighted random_uniform; do
  $PY -m gen.train_ddpm data/sets/$RUN $s --bank data/crops/10m_64.npz --out $M/10m_64_$s --amp fp16 --steps 15000
done
for s in path_weighted random_uniform; do
  $PY -m gen.train_ddpm data/sets/$RUN $s --out $M/40m_64_$s --amp fp16 --steps 15000
done
echo "[dreams_v2_train] all done"
