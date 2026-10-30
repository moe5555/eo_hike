#!/usr/bin/env bash
# Hikes 29.10, part 2 (notes/hikes_2910/): Bored and Globalist, 5,000 steps each from Paris, seed 0, Mac CPU.
# Waits for the 1,000-step batch (scripts/hikes_2910.sh) to finish, then walks one after another: two walkers
# starting in the same place would fetch the same tiles into the shared cache at the same moment.
cd "$(dirname "$0")/.."
PY=.venv/bin/python
until grep -q "all done" runs/hikes_2910.log 2>/dev/null; do sleep 60; done
for c in bored globalist; do
  echo "=== $(date '+%F %T') configs/h2910_${c}_paris.yaml --seed 0"
  if $PY -m agent.walk configs/h2910_${c}_paris.yaml --seed 0; then
    $PY analysis/hike_viewer.py runs/h2910_${c}_paris_s0 2>&1 | grep '^\[hike\]'
  else
    echo "=== FAILED: h2910_${c}_paris"
  fi
done
echo "=== $(date '+%F %T') all done"
